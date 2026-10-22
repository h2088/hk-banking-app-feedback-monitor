"""Conservative script routing and explicit Traditional/Simplified/Cantonese terms.

No source text is normalized, translated or rewritten for storage. Matching only
uses NFKC copies. Han-only text can be ambiguous (Chinese vs Japanese kanji);
the HK banking context is an assumption, documented and sampled for review.
"""
import re
import unicodedata
import v2_rules as en

THEMES = en.THEMES
HAN = re.compile(r"[\u3400-\u9fff\U00020000-\U0002fa1f]")
OTHER_SCRIPT = re.compile(r"[\u3040-\u30ff\uac00-\ud7af]")
ACRONYMS = {"app","apps","sc","scb","hsbc","bochk","boc","hk","hkd","usd","otp","fps","hkid","id","ios","android","iphone","ipad","atm","pdf","ui","ux","sms","wifi","nfc","qr","octopus","payme","pay","apple","google","androids"}
# Exact body decisions from reading the new window exclusions. Shared short
# words such as 'ok' and emoji-only records remain uncertain.
ZH = {
 "app_stability_performance": ["閃退","闪退","崩潰","崩溃","死機","死机","卡死","卡頓","卡顿","當機","当机","白屏","黑屏","無反應","无反应","冇反應","沒有反應","没有反应","載入","载入","加載","加载","連線","连线","連接","连接","錯誤","错误","開不到","開唔到","打不开","打不開","打唔開","進不去","進唔到","进不去","慢","lag","不穩定","不稳定","唔穩定"],
 "login_authentication_access": ["登入","登錄","登录","密碼","密码","認證","认证","驗證","验证","保安編碼","保安编码","人面","人臉","人脸","臉部","脸部","指紋","指纹","生物識別","生物识别","流動保安","流动保安","鎖定","锁定","鎖住","锁住","身份證","身分證","身份证","啟動","启动","啟用","启用"],
 "transfers_payments_cards": ["轉賬","轉帳","转账","轉數快","转数快","匯款","汇款","付款","支付","繳費","缴费","繳款","缴款","信用卡","提款卡","扣賬卡","扣账卡","借記卡","借记卡","收款","交易","提款","存款","增值","匯出","汇出"],
 "usability_navigation_design": ["介面","界面","版面","佈局","布局","設計","设计","字體","字体","字太","字好細","字好细","字細","字细","按鈕","按钮","導航","导航","菜單","菜单","選單","选单","易用","好用","難用","难用","唔好用","不方便","方便","複雜","复杂","繁複","繁复","找不到","搵唔到","搵不到","用戶體驗","用户体验","操作"],
 "customer_support_service": ["客服","客戶服務","客户服务","熱線","热线","致電","致电","打電話","打电话","打比","打畀","聯絡","联络","聯繫","联系","回覆","回复","跟進","跟进","職員","职员","分行"],
 "account_registration": ["開戶","开户","開戶口","戶口","户口","賬戶","账户","帳戶","註冊","注册","登記","登记"],
 "balance_statements_history": ["餘額","余额","結餘","结余","月結單","月结单","對賬單","对账单","對帳單","帳單","賬單","账单","交易紀錄","交易記錄","交易记录","歷史紀錄","历史记录","明細","明细"],
 "security_fraud_trust": ["安全","保安","詐騙","诈骗","騙局","骗局","騙人","骗人","呃人","欺詐","欺诈","私隱","隐私","隱私","洩漏","泄露","可信","信任","盜用","盗用","盜取","盗取"],
 "language_localization": ["中文","英文","繁體","繁体","簡體","简体","廣東話","广东话","粵語","粤语","語言","语言","翻譯","翻译"],
 "fees_rates": ["手續費","手续费","收費","收费","費用","费用","利息","利率","匯率","汇率","兌換率","兑换率"],
 "feature_request": ["建議","建议","希望","請新增","请新增","可否","可唔可以","能否","最好可以","應該","应该","請加入","请加入","改進","改进","改善","請修正","请修正","請減少","请减少","需要減低","需要减低"],
}
ZH["app_stability_performance"] += ["彈app","弹app","彈出app","弹出app","等待","需時","需时","耗時","耗时","用唔到","用不了","不能用","無法使用","无法使用","未能提供服務","未能提供服务","服務繁忙","服务繁忙"]
ZH["transfers_payments_cards"] += ["轉款","转款"]
ZH["account_registration"] += ["帳號","账号","賬號"]
ZH["security_fraud_trust"] += ["風險","风险","無障礙","无障碍"]


def language_group(row):
    if not row["text"].strip():
        return "excluded", "Empty customer body; saved as evidence"
    if row.get("language_override_applied"):
        return row["analysis_language"], row["analysis_language_method"]
    text = (row.get("title") or "") + "\n" + row["text"]
    if HAN.search(text) and not OTHER_SCRIPT.search(text):
        words = {w.lower() for w in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text) if w.lower() not in ACRONYMS}
        return ("mixed" if len(words) >= 3 else "chinese"), "Han script, no kana/Hangul; mixed if >=3 distinct non-acronym Latin words (HK-context heuristic)"
    if OTHER_SCRIPT.search(text):
        return "excluded", "Kana/Hangul present; Chinese-only or Chinese-English attribution uncertain"
    if row["language_status"] == "english":
        return "english", "Preserved English detector or exact-text review decision"
    return "excluded", "No accepted English or Chinese evidence; original status retained"


def classify(row):
    result = en.classify(row)
    text = unicodedata.normalize("NFKC", result["comment_text_for_analysis"])
    # Insert boundaries only in a matching copy for '一直loading', 'password之後'.
    separated = re.sub(r"(?<=[A-Za-z])(?=[\u3400-\u9fff])|(?<=[\u3400-\u9fff])(?=[A-Za-z])", " ", text)
    hits = [key for key in THEMES if key in result["themes"] or any(p.search(separated) for p in en.original.THEME_RE[key][1]) or any(term in text.casefold() for term in ZH[key])]
    result.update(themes=hits, theme_labels=[THEMES[k][0] for k in hits], theme_count=len(hits),
                  primary_theme=hits[0] if hits else "unclassified", primary_theme_label=THEMES[hits[0]][0] if hits else "Unclassified / insufficient text")
    if row["analysis_language"] != "english":
        # Do not apply English word counts or a few English tokens to Chinese sentiment.
        result.update(text_sentiment_rule="not_evaluated_chinese", text_positive_hits=None, text_negative_hits=None,
                      text_polarity_score=None, sentiment_rating_text_agreement=None)
    result["han_character_count"] = len(HAN.findall(text))
    result["short_text_for_theme_review"] = result["word_count_for_analysis"] <= 4 and result["han_character_count"] <= 8
    result["theme_method"] = "V2 English regex + V3 explicit Traditional/Simplified/Cantonese substring rules"
    return result


def belongs(row, scope):
    return scope == "all" or row["analysis_language"] == scope or (scope == "chinese" and row["analysis_language"] == "mixed")


def metrics(rows, name, extra):
    result = en.metrics(rows, name, extra)
    for field in ("text_negative_rule_count", "text_negative_rule_rate", "text_sentiment_evaluated_count"):
        result.pop(field, None)
    return result


theme_metrics = en.theme_metrics
normalized = en.normalized
