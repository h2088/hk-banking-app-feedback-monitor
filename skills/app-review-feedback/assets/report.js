const DATA = __DATA__;
const PAGE_SIZE = 60;
let currentPage = 0;
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const percent = value => value == null ? '无样本' : (100 * value).toFixed(2) + '%';
const stars = n => '★'.repeat(n) + '☆'.repeat(5-n);
const appName = key => DATA.apps.find(a => a.key === key)?.name ?? key;
function populate() {
  DATA.apps.forEach(a => { const o = document.createElement('option'); o.value = a.key; o.textContent = a.name; $('appFilter').append(o); });
  DATA.theme_names.forEach(t => { const o = document.createElement('option'); o.value = t.key; o.textContent = t.label; $('themeFilter').append(o); });
  const max = Math.max(1, ...DATA.monthly.map(m => m.review_count));
  $('monthlyChart').innerHTML = DATA.monthly.map(m => '<div class="month-row"><strong>' + esc(m.month) + '</strong><div><div class="bar" style="width:' + (m.review_count/max*100) + '%;background:#2865d8;height:14px"></div><div class="small">' + m.review_count + ' 条；' + DATA.apps.map(a => esc(a.name) + ' ' + m.apps[a.key].review_count + ' 条，1–2 星 ' + percent(m.apps[a.key].negative_rate_rating_1_2)).join(' ｜ ') + '</div></div></div>').join('');
}
function filterRows() {
  const q = $('search').value.toLowerCase();
  return DATA.comments.filter(r => (!$('appFilter').value || r.app_key === $('appFilter').value)
    && (!$('ratingFilter').value || r.rating === Number($('ratingFilter').value))
    && (!$('sentimentFilter').value || r.rating_sentiment === $('sentimentFilter').value)
    && (!$('themeFilter').value || r.themes.includes($('themeFilter').value))
    && (!q || [r.text,r.title,...r.theme_labels].join(' ').toLowerCase().includes(q)));
}
function renderComments() {
  const filtered = filterRows(), pages = Math.max(1,Math.ceil(filtered.length / PAGE_SIZE));
  currentPage = Math.min(Math.max(0,currentPage),pages-1);
  const offset = currentPage * PAGE_SIZE, visible = filtered.slice(offset,offset+PAGE_SIZE);
  $('resultCount').textContent = '显示 ' + (filtered.length ? offset+1 : 0) + '–' + (offset+visible.length) + ' / ' + filtered.length + ' 条匹配评论（按时间从新到老）';
  $('pageInfo').textContent = '第 ' + (currentPage+1) + ' / ' + pages + ' 页';
  $('prevPage').disabled = currentPage === 0; $('nextPage').disabled = currentPage >= pages-1;
  $('empty').hidden = filtered.length > 0;
  $('commentRows').innerHTML = visible.map(r => '<tr data-record-key="' + esc(r.record_key) + '"><td><time datetime="' + esc(r.review_time_hk) + '">' + esc(r.review_time_hk.replace('T',' ').replace('+08:00','')) + '</time></td><td>' + esc(appName(r.app_key)) + '</td><td class="stars">' + stars(r.rating) + '</td><td>' + ({negative:'负面',neutral:'中性',positive:'正面'}[r.rating_sentiment]) + '</td><td>' + (r.theme_labels.map(t => '<span class="pill">' + esc(t) + '</span>').join(' ') || '未分类') + '</td><td><div class="comment-text">' + (r.title ? '<div class="comment-title">' + esc(r.title) + '</div>' : '') + esc(r.text) + '</div><div class="comment-meta">评论 ID：' + esc(r.review_id) + (r.short_text_for_theme_review ? '<br>短评论，主题证据有限' : '') + '</div></td><td><a target="_blank" rel="noreferrer" href="' + esc(r.source_url) + '">来源核查</a><br><a target="_blank" rel="noreferrer" href="' + esc(r.raw_response_workspace_path) + '">已存原始响应</a></td></tr>').join('');
}
['search','appFilter','ratingFilter','sentimentFilter','themeFilter'].forEach(id => $(id).addEventListener('input',() => { currentPage=0; renderComments(); }));
$('prevPage').onclick = () => { currentPage--; renderComments(); };
$('nextPage').onclick = () => { currentPage++; renderComments(); };
populate(); renderComments();
