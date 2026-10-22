"""Bind actual, individually authored reading notes to the prepared sample."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"engine"))
from feedback_io import dump,load,sha,now

# These notes were authored after reading all 47 rendered source samples.
# Reusing this script on changed input is blocked by the sample hash below.
NOTES=[
("plausible","English: forced closure after update directly supports stability. One star agrees with negative wording; no business journey is named."),
("insufficient_text","English: 'good' supports the five-star proxy but gives no business topic. Correctly retained and unclassified."),
("plausible","Cantonese/Traditional Chinese: repeated crashes at login support stability and authentication. One star is consistent with frustration."),
("plausible","Chinese: transfer completes but display synchronization is slow; performance and transfers are both relevant. Three stars remains neutral by rating despite critical text."),
("plausible","Chinese: '好用' praises usability. Five-star positive; the topic is a positive mention, not a complaint."),
("limitation_noted","Mixed Cantonese/English: redundant login push notifications while opening stocks. Login label is relevant; no notification-specific or investment topic exists."),
("plausible","Mixed Cantonese/English: crashes after username/password entry, plus request for screen captures after transfers/account opening. Five topics are supported. Three-star neutral proxy masks critical text."),
("plausible","English: poor verification process directly matches authentication. One star agrees; source text does not identify the exact failure stage."),
("limitation_noted","English: worries about visible user name and doxxing support security/privacy. Three stars is neutral by proxy; a suggested change is not captured by the limited suggestion patterns."),
("insufficient_text","English: 'Fast and Great' is positive and five-star, but does not specify a journey. Unclassified is reasonable; fast is not a performance-problem assertion."),
("limitation_noted","Simplified/Cantonese Chinese: objects to Samsung utility/accessibility risk blocking. Security risk terms are relevant; exact installation/access policy failure is not confirmed."),
("plausible","Cantonese: '唔好用' is negative usability wording. Three-star neutral rating differs from the text; the proxy is intentionally retained."),
("plausible","Chinese: convenience and speed praise supports usability. Five-star positive; no concrete complaint or defect is stated."),
("limitation_noted","Chinese crash report includes HyperOS, Beta and device/version tokens, triggering mixed. Stability fits, but technical identifiers do not prove substantive bilingual prose."),
("plausible","Mixed Cantonese/English: asks for fewer logoff animations and back-button exit. Usability and explicit request fit; three stars stays neutral by rating."),
("plausible","English: 'not user friendly' is a usability criticism. One star is consistent; no specific journey is stated."),
("plausible","English: poor face recognition supports authentication. Three-star neutral rating is more favorable than the critical wording."),
("insufficient_text","English: 'good' gives no concrete journey. Five-star positive and unclassified topic are appropriate for triage."),
("insufficient_text","Chinese: '非常差' expresses broad dissatisfaction. One-star negative fits; no topic should be invented."),
("plausible","Chinese: '太卡顿了' directly reports lag. Stability fits while the source three-star rating remains neutral."),
("plausible","Chinese: easy interface operation is usability praise. Five-star positive, not a reported defect."),
("limitation_noted","Mixed Cantonese/English: criticizes username/password login design. Authentication fits; a desired alternative is implied rather than explicitly matched as a feature request."),
("limitation_noted","Mixed Chinese/English: details risk checks, crashes and fingerprint/login behavior. Stability, authentication and risk mentions fit. Feature-request is an overmatch from '不应该出现'; this is descriptive, not a requested feature."),
("plausible","English: small fonts and changing layout obstruct urgent card suspension amid suspected scam. Design, cards and security are supported; one-star negative agrees."),
("plausible","English: questionnaire exceeds viewport on iPhone and close button is hard to find. Usability fits. Three-star neutral is a rating proxy, not a statement of satisfaction."),
("insufficient_text","English: title 'Easy' and body 'Easy to make' are positive but underspecified. Five-star and unclassified are retained without assuming a journey."),
("plausible","Cantonese/Traditional Chinese: password recovery terms screen causes app to exit. Authentication and stability fit after adding the '彈app' expression."),
("plausible","Traditional Chinese: asks for reduced graphics/animation and waiting at login. Performance, authentication and feature-request fit; three-star neutral retains source rating."),
("plausible","Traditional Chinese: easy layout and selection are usability praise. Five stars matches positive wording."),
("limitation_noted","Mixed Cantonese/English: angry about scratch-card marketing and a paid membership offer. One star agrees; taxonomy has no marketing topic, so unclassified is an acknowledged coverage gap."),
("plausible","English: recurring unspecified error message fits stability/error screening. One star agrees, but exact error and root cause are unknown."),
("plausible","English: explicitly suggests consolidating financial apps to save storage. Feature request fits; the text does not report an actual payment failure."),
("insufficient_text","English: Nice/Good is generic praise. Five stars aligns; no journey topic can be justified."),
("plausible","Cantonese with 'loading': app loads continuously then service unavailable. Stability fits. Generic online service wording is not customer support; rule avoids that false support match."),
("plausible","Simplified Chinese: redesign request, login/FPS popup, missing transaction details and complex navigation support all five assigned themes. Three-star neutral masks clear criticisms."),
("insufficient_text","Chinese: says experience is good and friendly to mainland users. Five stars fits, but no specific app journey is identified."),
("limitation_noted","Mixed title/body: step count does not update and waits a long time. One-star dissatisfaction is clear. Current performance patterns miss this phrasing, so unclassified is a known false negative."),
("limitation_noted","Chinese title with English body praises the app and hopes policy does not affect service. Mixed routing is reasonable. Five stars fits; generic maintenance hope is not detected as a feature request."),
("plausible","English: repeated HKID scanning failure on a stated phone model supports authentication. One star fits; no device compatibility cause is confirmed."),
("plausible","English: title suggests improvement and body requests one-click credit-card payment. Payment/cards and feature request are supported; three-star neutral is retained."),
("plausible","English: title identifies first term deposit and body says easy. Deposit/payment theme is a mention, not a failure; five-star positive fits."),
("plausible","Traditional Chinese: identity/photo and face recognition fail after device change; old phone also cannot log in. Authentication fits; source text alone cannot establish cause."),
("insufficient_text","Cantonese: title and body repeat vague dissatisfaction with unclear practices. Three-star neutral is retained; no specific journey can be responsibly assigned."),
("plausible","Traditional Chinese: fast transfer is positive transfer feedback. Five stars agrees; this is not a transfer complaint."),
("plausible","Mixed Cantonese/English: FaceID removed after upgrade, registration failure, locked account and branch visit. Authentication, support and registration all fit; one star agrees."),
("plausible","Mixed Cantonese/English: app hangs when sharing a saved screen through WhatsApp. Stability fits after matching Latin terms adjacent to Han; three-star neutral remains a proxy."),
("plausible","Chinese title with English body: easy to use and very good. Mixed routing and usability praise fit; five stars agrees."),
]

def main():
    sample=load(ROOT/"data/analysis/validation_sample.json")
    assert len(sample)==len(NOTES)==47
    # Expected hash is bound after actual sample reading, not computed as consent.
    expected=load(ROOT/"review_binding.json")["sample_sha256"]
    assert expected==sha(ROOT/"data/analysis/validation_sample.json")
    dump(ROOT/"manual_review.json",dict(status="reviewed",reviewer="Codex agent",reviewed_at_utc=now(),sample_sha256=expected,
        method="Actual reading of all 47 stratified source comments; language-boundary cases were separately read. Not independent human labeling or an accuracy estimate.",
        reviews=[dict(record_key=r["record_key"],fingerprint=r["fingerprint"],theme_assessment=a,notes=n) for r,(a,n) in zip(sample,NOTES)]))
    print("Recorded 47 individually authored agent reading judgments")

if __name__=="__main__":
    main()
