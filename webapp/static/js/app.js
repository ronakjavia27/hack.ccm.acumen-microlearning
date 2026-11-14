
// =====================================================================
// DATA (injected from Python as the #boot JSON block; see render_dashboard)
// =====================================================================
const BOOT = JSON.parse(document.getElementById('boot').textContent);
const SPEC_VAR = BOOT.spec_vars;
const SPECS = BOOT.spec_labels.map(function(n){ return {name:n, var:SPEC_VAR[n]}; });
const TYPES = BOOT.type_list;

// Specialty normalization (matches Python build_specialty_map)
const SPEC_MAP = {
  "cardiology": "Cardiology",
  "neurology": "Neurology",
  "nephrology": "Nephrology",
  "pulmonology": "Pulmonology",
  "gastroenterology": "Gastroenterology",
  "infectious diseases": "Infectious Diseases",
  "rheumatology": "Rheumatology",
  "immunology": "Immunology",
  "sepsis": "Sepsis",
  "toxicology": "Toxicology",
  "hepatology": "Hepatology",
  "oncology": "Oncology",
  "hematology": "Hematology",
  "other": "Other",
  "multisystem": "Multisystem",
  "nutrition": "Nutrition",
  "trauma": "Trauma",
  "surgery": "Surgery",
  "endocrinology": "Endocrinology",
  "obstetrics and gynecology": "Obstetrics And Gynecology",
  "obstetrics & gynecology": "Obstetrics And Gynecology",
  "obgyn": "Obstetrics And Gynecology",
  "cardio": "Cardiology",
  "cardiovascular": "Cardiology",
  "neuro": "Neurology",
  "nephro": "Nephrology",
  "pulmo": "Pulmonology",
  "gi": "Gastroenterology",
  "heme": "Hematology",
  "onc": "Oncology"
};
function normalizeSpec(name) {
  if (!name) return 'Other';
  var key = String(name).toLowerCase().replace(/[_\-]/g, ' ').replace(/&/g, 'and').trim();
  return SPEC_MAP[key] || name;
}

const baseDataset = BOOT.articles;
const allPearls = BOOT.pearls;
const SUBTOPIC_MAP = BOOT.subtopic_map;
const showDisclaimer = BOOT.show_disclaimer;

// Trial data
const TRIAL_INDEX = BOOT.trial_index;
const TRIAL_SPECS = BOOT.trial_spec_labels;
const TRIAL_SPEC_VAR = BOOT.trial_spec_vars;
const TRIAL_SPEC_COUNTS = BOOT.trial_spec_counts;
const TRIAL_SUBTOPIC_MAP = BOOT.trial_subtopic_map;
const TRIAL_RESULT_CATS = BOOT.trial_result_cats;
const TRIAL_TYPES = BOOT.trial_types_list;

// Condensed trial data
const CONDENSED_INDEX = BOOT.condensed_index;
const CONDENSED_SYSTEMS = BOOT.condensed_systems;
const CONDENSED_RESULT_CATS = BOOT.condensed_result_cats;
const CONDENSED_TYPES = BOOT.condensed_types_list;

// Theory flashcard decks (unified store) + theory notes
const allFlashcardDecks = BOOT.flashcard_decks;
const THEORY_SPEC_VAR = BOOT.theory_spec_vars;
const THEORY_SUBTOPIC_MAP = BOOT.theory_subtopic_map;
const THEORY_NOTES = BOOT.theory_notes;

// Cross-linking index (papers ↔ guidelines ↔ theory ↔ decks) precomputed by acumen_core/linker.py
const RELATED_CATALOG = BOOT.related_catalog;
const RELATED_INDEX = BOOT.related_index;
const RELATED_META = BOOT.related_meta;
const RELATED_REASONS = ['same topic','guideline recommendation','complementary','background theory','practice deck','shared concept'];

// Feature flags (resolved server-side: defaults + per-user overrides)
const USER_FEATURES = BOOT.user_features;
const USER_IS_ADMIN = BOOT.user_is_admin;
const ADMIN_FEATURE_FLAGS = BOOT.admin_feature_flags;

let _trialFilterState = { specialty: '', result_category: '', trial_type: '' };
let _currentTrialList = [];
let _currentTrialIdx = -1;
let _currentTrialSlug = '';
let _currentCondensedRef = '';
let _bookmarks = {items: {}, folders: {}};
let _bookmarkMeta = {};
let _bookmarksFolderFilter = null;
let _bmNewFolderColor = '#E8B778';
const BM_FOLDER_COLORS = ['#E8B778','#0C8A8B','#2DD4CF','#8B5CF6','#EF4444','#10B981','#D97706','#6B7280'];

// Theory flashcard study state
let _theoryMode = null; // null = hero, 'notes' = Theory Topics, 'flashcards' = decks
let _theoryActiveSpecs = new Set(allFlashcardDecks.map(function(d){ return normalizeSpec(d.specialty); }));
let _theorySavedOnly = false;
let _notesSavedOnly = false;
let _notesActiveSpecs = new Set();
let _notesActiveSubtopic = null;
let _currentTheoryNote = null;
let _theoryTableOverlayOpen = false;
let _theoryTableFitActive = false;
let _theoryActiveSubtopic = null;
let _currentDeck = null;
let _currentCardIdx = 0;
let _theoryCardOrder = [];
let _theoryViewMode = 'single';
let _theoryFlipped = false;
let _theoryListCollapsed = false; // card list collapses into a dropdown when a card is open
let _theoryStudyFromList = false; // study was entered from the per-deck card list
let _restoring = false; // true while restoring from history/deep links (no pushes)
let _theorySearchTimers = {};
// True when the browser can do real 3D card flips (backface-visibility).
// False -> the reader falls back to display-swapping (.no-3d) so faces never stack.
let _css3d = (function(){
  try { return !!(window.CSS && window.CSS.supports && window.CSS.supports('backface-visibility','hidden')); }
  catch(e) { return false; }
})();

// =====================================================================
// STATE
// =====================================================================
const filterState = {
  specialties: Object.fromEntries(SPECS.map(function(s){ return [s.name,true]; })),
  types: Object.fromEntries(TYPES.map(function(t){ return [t,true]; })),
};
let activePearlSpecs = new Set(SPECS.map(function(s){ return s.name; }));
let pearlsPageSize = 25;
let pearlsShown = pearlsPageSize;
let activeSubtopic = null;

// =====================================================================
// HELPERS
// =====================================================================
function pillHTML(spec, label){
  var v = SPEC_VAR[spec];
  if (!v) v = '--spec-other';
  return '<span class="pill" style="background:color-mix(in srgb, var('+v+') 18%, transparent); color:var('+v+')"><span class="dot" style="background:var('+v+')"></span>'+label+'</span>';
}

function docCardHTML(p){
  var sysNorm = normalizeSpec(p.system);
  var v = SPEC_VAR[sysNorm] || '--spec-other';
  return '<button class="doc-card" data-open-paper="'+p.id+'">'+
    '<div class="doc-stripe" style="background:var('+v+')"></div>'+
    '<div class="doc-inner">'+
      '<div class="doc-top">'+pillHTML(sysNorm, sysNorm)+'<span class="type-tag">'+p.type+'</span></div>'+
      '<p class="doc-title">'+p.title+'</p>'+
      '<p class="doc-snippet">'+(p.authors!=='Unknown Authors' ? '&mdash; '+p.authors : '')+'</p>'+
    '</div>'+
  '</button>';
}

function emptyStateHTML(label){
  return '<p style="color:var(--ink-muted);padding:20px 4px">No '+label+' match these filters. Try clearing a specialty or type.</p>';
}

// =====================================================================
// VIEW SWITCHING
// =====================================================================
function showView(name){
  if(name==='users' && !USER_IS_ADMIN) return false;
  // Feature flag check: block views that the user doesn't have access to
  var featureMap = {
    'trials': 'trials',
    'trials-esbicm': 'trials',
    'trials-condensed': 'condensed_trials',
    'trials-specialty': 'trials',
    'trials-detail': 'trials_detail',
    'condensed-system': 'condensed_trials',
    'condensed-detail': 'trials_detail',
    'papers': 'papers',
    'guidelines': 'guidelines',
    'pearls': 'pearls',
    'search': 'search',
    'bookmarks': 'bookmarks',
    'theory': 'theory'
  };
  var requiredFeature = featureMap[name];
  if (requiredFeature && !USER_IS_ADMIN && !USER_FEATURES[requiredFeature]) {
    return false;
  }
  document.querySelectorAll('.view').forEach(function(v){ v.classList.remove('active'); });
  var target = document.getElementById('view-'+name);
  (target || document.getElementById('view-home')).classList.add('active');
  document.querySelectorAll('[data-view]').forEach(function(el){ el.classList.toggle('active', el.dataset.view===name); });
  window.scrollTo({top:0, behavior:'instant'});
  closeDrawer(); closeSheet();
  if(name==='home'){ renderHomeHero(); renderHomeStats(); renderHomeSpecGrid(); }
  if(name==='papers') renderPapers();
  if(name==='guidelines') renderGuidelines();
  if(name==='pearls'){ renderPearlChips(); renderPearls(); }
  if(name==='trials') renderTrials();
  if(name==='trials-esbicm') renderESBICM();
  if(name==='trials-condensed') renderCondensedTrials();
  if(name==='bookmarks') renderBookmarks();
  if(name==='users'){ loadUsers(); }
  if(name==='theory'){
    var activeView = document.querySelector('.view.active');
    if(activeView && activeView.id==='view-theory'){
      if(_theoryMode) theoryBackToHero();
    } else {
      renderTheoryPane(_theoryMode);
    }
  }
  return true;
}

// =====================================================================
// HOME
// =====================================================================
function getDailyIndex(){
  var t=new Date().toISOString().split('T')[0];
  var h=0;for(var i=0;i<t.length;i++){h=((h<<5)-h)+t.charCodeAt(i);h=h&h;}
  return Math.abs(h)%(baseDataset.length||1);
}

var _pearlOfDay = null;
var _currentPearlList = [];
var _currentPearlIndex = -1;

// Serendipity Mode state
var _serendipityPearls = [];
var _serendipityIndex = -1;
var _serendipityHistory = [];
var _serendipityMode = false;

var _readerHistoryStack = [];
function renderHomeHero(){
  if (!baseDataset.length) { document.getElementById('homeHero').innerHTML = ''; return; }
  var sorted = [].concat(baseDataset).sort(function(a,b){ return parseInt(a.id)-parseInt(b.id); });
  var paperOfDay = sorted[getDailyIndex()];
  _pearlOfDay = allPearls.length ? allPearls[Math.floor(Math.random()*allPearls.length)] : null;
  var pv = SPEC_VAR[paperOfDay.system] || '--spec-other';
  document.getElementById('homeHero').innerHTML =
    '<div class="card" data-open-paper="'+paperOfDay.id+'" tabindex="0" role="button" aria-label="Open paper of the day">'+
      '<div class="stripe" style="background:var('+pv+')"></div>'+
      '<div class="card-body">'+
        '<p class="eyebrow" style="margin-bottom:8px">Paper of the day</p>'+
        pillHTML(paperOfDay.system, paperOfDay.system+' &middot; '+paperOfDay.type)+
        '<h3>'+escapeHtml(paperOfDay.title)+'</h3>'+
        '<p>'+(paperOfDay.authors && paperOfDay.authors!=='Unknown Authors' ? '&mdash; '+escapeHtml(paperOfDay.authors) : '')+'</p>'+
      '</div>'+
    '</div>'+
    (_pearlOfDay ? (
      '<div class="card" data-open-pearl="day" tabindex="0" role="button" aria-label="Open pearl of the day">'+
        '<div class="stripe" style="background:var(--spec-other)"></div>'+
        '<div class="card-body">'+
          '<p class="eyebrow" style="margin-bottom:8px">Pearl of the day</p>'+
          pillHTML(_pearlOfDay.system || 'General', (_pearlOfDay.system || 'General')+' &middot; Pearl')+
          '<h3 style="font-size:1rem">"'+escapeHtml((_pearlOfDay.pearl||'').substring(0,120))+(_pearlOfDay.pearl && _pearlOfDay.pearl.length>120?'&hellip;':'')+'"</h3>'+
          '<p>Tap to read the full context.</p>'+
        '</div>'+
      '</div>'
    ) : '');
}

function renderHomeStats(){
  var papersCount = baseDataset.filter(function(a){ return a.type.toLowerCase()!=='guideline'; }).length;
  var guidelinesCount = baseDataset.filter(function(a){ return a.type.toLowerCase()==='guideline'; }).length;
  document.getElementById('homeStats').innerHTML =
    '<div class="stat-item"><b>'+papersCount+'</b>papers</div>'+
    '<div class="stat-item"><b>'+guidelinesCount+'</b>guidelines</div>'+
    '<div class="stat-item"><b>'+allPearls.length+'</b>pearls</div>'+
    '<div class="stat-item"><b>'+THEORY_NOTES.length+'</b>theory topics</div>';
}

// =====================================================================
// WHAT'S NEW OVERLAY
// =====================================================================
var _WHATSNEW_DAYS = 14;
function _wnIsNew(d){
  if(!d) return false;
  var t = new Date(d);
  if(isNaN(t.getTime())) return false;
  return (Date.now() - t.getTime()) / 86400000 <= _WHATSNEW_DAYS;
}
function _wnDateStr(d){ return d ? String(d).substring(0,10) : ''; }

var _wnFilter = 'all';
function _wnLatest(arr, n){
  return [].concat(arr).sort(function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); }).slice(0,n);
}
function _wnPapers(){
  return [].concat(baseDataset).filter(function(a){ return (a.type||'').toLowerCase()!=='guideline'; });
}
function _wnGuidelines(){
  return [].concat(baseDataset).filter(function(a){ return (a.type||'').toLowerCase()==='guideline'; });
}
function renderWhatsNewChips(){
  var capped = {
    papers: _wnLatest(_wnPapers(), 12).length,
    guidelines: _wnLatest(_wnGuidelines(), 12).length,
    theory: _wnLatest(THEORY_NOTES, 8).length
  };
  var counts = {
    all: capped.papers + capped.guidelines + capped.theory,
    papers: capped.papers,
    guidelines: capped.guidelines,
    theory: capped.theory
  };
  var defs = [
    ['all','All',counts.all],
    ['papers','Papers',counts.papers],
    ['guidelines','Guidelines',counts.guidelines],
    ['theory','Theory',counts.theory]
  ];
  var box = document.getElementById('whatsNewChips');
  if(!box) return;
  box.innerHTML = defs.map(function(d){
    return '<button class="chip'+( _wnFilter===d[0]?' active':'')+'" data-wn-filter="'+d[0]+'" style="--chip-color:var(--accent)">'+d[1]+' <span class="chip-count">'+d[2]+'</span></button>';
  }).join('');
}
function _wnRow(p, kind){
  var v = SPEC_VAR[p.system] || '--spec-other';
  return '<button class="related-row" data-open-paper="'+p.id+'">'+
    '<span class="related-row-top">'+
      '<span class="related-kind">'+kind+'</span>'+
      '<span class="related-title">'+escapeHtml(p.title)+'</span>'+
      (_wnIsNew(p.date_added)?'<span class="wn-new">New</span>':'')+
    '</span>'+
    '<span class="related-reason"><span class="dot" style="background:var('+v+');display:inline-block;vertical-align:middle"></span> '+escapeHtml(p.system)+' &middot; '+escapeHtml(_wnDateStr(p.date_added))+'</span>'+
  '</button>';
}
function renderWhatsNew(){
  var papers = [], guidelines = [], notes = [];
  if(_wnFilter==='all' || _wnFilter==='papers') papers = _wnLatest(_wnPapers(), 12);
  if(_wnFilter==='all' || _wnFilter==='guidelines') guidelines = _wnLatest(_wnGuidelines(), 12);
  if(_wnFilter==='all' || _wnFilter==='theory') notes = _wnLatest(THEORY_NOTES, 8);
  var html = '';
  if(papers.length){
    html += '<div class="related-group-label">'+(_wnFilter==='all'?'Latest Papers':'Papers')+'</div>';
    html += papers.map(function(p){ return _wnRow(p, 'Paper'); }).join('');
  }
  if(guidelines.length){
    html += '<div class="related-group-label">'+(_wnFilter==='all'?'Latest Guidelines':'Guidelines')+'</div>';
    html += guidelines.map(function(p){ return _wnRow(p, 'Guideline'); }).join('');
  }
  if(notes.length){
    html += '<div class="related-group-label">Latest Theory Topics</div>';
    html += notes.map(function(n){
      return '<button class="related-row" data-theory-note="'+escapeHtml(n.id)+'">'+
        '<span class="related-row-top">'+
          '<span class="related-kind">Theory</span>'+
          '<span class="related-title">'+escapeHtml(n.title)+'</span>'+
          (_wnIsNew(n.date_added)?'<span class="wn-new">New</span>':'')+
        '</span>'+
        '<span class="related-reason">'+escapeHtml(n.system||'General')+' &middot; '+escapeHtml(n.subtopic||'General')+' &middot; '+escapeHtml(_wnDateStr(n.date_added))+'</span>'+
      '</button>';
    }).join('');
  }
  var emptyText = '<div class="related-empty"><span class="icon">&#10024;</span><p>Nothing new here yet &mdash; check back soon.</p></div>';
  if(_wnFilter==='papers') emptyText = '<div class="related-empty"><span class="icon">&#10024;</span><p>No new papers yet &mdash; check back soon.</p></div>';
  if(_wnFilter==='guidelines') emptyText = '<div class="related-empty"><span class="icon">&#10024;</span><p>No new guidelines yet &mdash; check back soon.</p></div>';
  if(_wnFilter==='theory') emptyText = '<div class="related-empty"><span class="icon">&#10024;</span><p>No new theory topics yet &mdash; check back soon.</p></div>';
  document.getElementById('whatsNewScroll').innerHTML = html || emptyText;
  document.getElementById('whatsNewMeta').textContent = 'Most recent additions — newest first';
}
function openWhatsNew(){
  renderWhatsNewChips();
  renderWhatsNew();
  document.getElementById('whatsNewOverlay').classList.add('open');
  document.body.classList.add('whatsnew-open');
}

function closeWhatsNew(){
  document.getElementById('whatsNewOverlay').classList.remove('open');
  document.body.classList.remove('whatsnew-open');
}

function renderHomeSpecGrid(){
  var specCounts = {};
  baseDataset.forEach(function(a){ specCounts[a.system] = (specCounts[a.system]||0)+1; });
  var sortedSpecs = Object.keys(specCounts).sort();
  document.getElementById('homeSpecGrid').innerHTML = sortedSpecs.map(function(s){
    var v = SPEC_VAR[s] || '--spec-other';
    return '<button class="spec-tile" data-spec-jump="'+s+'" style="--tile-color:var('+v+');border-left:3px solid var('+v+')">'+
      '<span class="dot" style="background:var('+v+')"></span>'+
      '<div style="font-weight:700;font-size:.88rem">'+s+'</div>'+
    '</button>';
  }).join('');
}

function jumpToSpecialty(name){
  activeSubtopic = null;
  navPushState('specialty');
  showView('specialty');
  renderSpecialty(name);
}

// =====================================================================
// FILTER PANEL (papers)
// =====================================================================
function filterGroupsHTML(){
  var specHTML = SPECS.map(function(s){
    return '<label><input type="checkbox" data-spec="'+s.name+'" '+(filterState.specialties[s.name]?'checked':'')+'><span class="dot" style="background:var('+s.var+')"></span>'+s.name+'</label>';
  }).join('');
  return ''+
    '<div class="filter-actions">'+
      '<button class="btn filter-reset" type="button" style="width:48%">Reset</button>'+
      '<button class="btn primary apply-btn" type="button" style="width:48%">Apply</button>'+
    '</div>'+
    '<div class="filter-group">'+
      '<h4>Specialty</h4>'+
      '<label><input type="checkbox" class="all-check" data-group="specialties"><strong>All</strong></label>'+
      specHTML+
    '</div>';
}

function updateAllCheckboxState(container, group){
  var allBox = container.querySelector('.all-check[data-group="'+group+'"]');
  if(!allBox) return;
  var boxes = [].slice.call(container.querySelectorAll(group==='specialties' ? '[data-spec]' : '[data-type]'));
  var checkedCount = boxes.filter(function(b){ return b.checked; }).length;
  allBox.checked = checkedCount===boxes.length;
  allBox.indeterminate = checkedCount>0 && checkedCount<boxes.length;
}

function renderFilterCheckboxes(){
  ['filterPanelDesktop','filterSheetBody','filterPanelGuidelines'].forEach(function(id){
    var el = document.getElementById(id);
    if(!el) return;
    el.innerHTML = filterGroupsHTML();
    updateAllCheckboxState(el,'specialties');
  });
}

function renderPapers(){
    var q = (document.getElementById('papersSearch').value || '').toLowerCase().trim();
    var sortVal = document.getElementById('papersSort').value;
    var articles = baseDataset.filter(function(p){ return p.type.toLowerCase()!=='guideline'; });
    var filtered = articles.filter(function(p){
      return filterState.specialties[normalizeSpec(p.system)] && (q==='' || p.title.toLowerCase().indexOf(q)!==-1);
    });
    if(sortVal==='newest'){
      filtered = [].concat(filtered).sort(function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); });
    } else {
      filtered = [].concat(filtered).sort(function(a,b){ return (a.date_added||'').localeCompare(b.date_added||''); });
    }
    document.getElementById('papersList').innerHTML = filtered.map(docCardHTML).join('') || emptyStateHTML('papers');
    document.getElementById('papersCount').textContent = 'Showing '+filtered.length+' of '+articles.length+' papers';
  }

function renderGuidelines(){
    var q = (document.getElementById('guidelinesSearch').value || '').toLowerCase().trim();
    var sortVal = document.getElementById('guidelinesSort').value;
    var filtered = baseDataset.filter(function(p){
      return p.type.toLowerCase()==='guideline' && filterState.specialties[normalizeSpec(p.system)] && (q==='' || p.title.toLowerCase().indexOf(q)!==-1);
    });
    if(sortVal==='newest'){
      filtered = [].concat(filtered).sort(function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); });
    } else {
      filtered = [].concat(filtered).sort(function(a,b){ return (a.date_added||'').localeCompare(b.date_added||''); });
    }
    document.getElementById('guidelinesList').innerHTML = filtered.map(docCardHTML).join('') || emptyStateHTML('guidelines');
    document.getElementById('guidelinesCount').textContent = 'Showing '+filtered.length+' guidelines';
  }

// =====================================================================
// SPECIALTY THREE-PANEL VIEW
// =====================================================================
function renderSpecialty(name){
  var v = SPEC_VAR[name] || '--spec-other';
  document.getElementById('specViewDot').style.background = 'var('+v+')';
  document.getElementById('specViewTitle').textContent = name;

  var papersInSpec = baseDataset.filter(function(p){ return normalizeSpec(p.system)===name && p.type.toLowerCase()!=='guideline'; });
  var guidelinesInSpec = baseDataset.filter(function(p){ return normalizeSpec(p.system)===name && p.type.toLowerCase()==='guideline'; });
  var pearlsInSpec = allPearls.filter(function(p){ return normalizeSpec(p.system)===name; });
  var theoryInSpec = THEORY_NOTES.filter(function(n){ return normalizeSpec(n.system)===name; });
  var decksInSpec = allFlashcardDecks.filter(function(d){ return normalizeSpec(d.specialty)===name; });

  /* apply subtopic filter */
  if(activeSubtopic){
    papersInSpec = papersInSpec.filter(function(p){ return (p.subtopic||p.system)===activeSubtopic; });
    guidelinesInSpec = guidelinesInSpec.filter(function(p){ return (p.subtopic||p.system)===activeSubtopic; });
    pearlsInSpec = pearlsInSpec.filter(function(p){ return (p.subtopic||p.system)===activeSubtopic; });
    theoryInSpec = theoryInSpec.filter(function(n){ return (n.subtopic||'General')===activeSubtopic; });
    decksInSpec = decksInSpec.filter(function(d){ return d.id===name+'/'+activeSubtopic || (d.subtopics||[]).indexOf(activeSubtopic)>=0; });
  }

  /* apply sort */
  var specPapersSort = document.getElementById('specPapersSort').value;
  if(specPapersSort==='newest'){
    papersInSpec = [].concat(papersInSpec).sort(function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); });
  } else {
    papersInSpec = [].concat(papersInSpec).sort(function(a,b){ return (a.date_added||'').localeCompare(b.date_added||''); });
  }
  var specGuidelinesSort = document.getElementById('specGuidelinesSort').value;
  if(specGuidelinesSort==='newest'){
    guidelinesInSpec = [].concat(guidelinesInSpec).sort(function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); });
  } else {
    guidelinesInSpec = [].concat(guidelinesInSpec).sort(function(a,b){ return (a.date_added||'').localeCompare(b.date_added||''); });
  }

  document.getElementById('specPanelPapersTitle').innerHTML = 'Papers ('+papersInSpec.length+')';
  document.getElementById('specPanelPapersBody').innerHTML = papersInSpec.map(docCardHTML).join('') || emptyStateHTML('papers');
  document.getElementById('specPanelPapers').classList.add('open');

  document.getElementById('specPanelGuidelinesTitle').innerHTML = 'Guidelines ('+guidelinesInSpec.length+')';
  document.getElementById('specPanelGuidelinesBody').innerHTML = guidelinesInSpec.map(docCardHTML).join('') || emptyStateHTML('guidelines');
  document.getElementById('specPanelGuidelines').classList.remove('open');

  document.getElementById('specPanelTheory').style.display = THEORY_NOTES.length ? '' : 'none';
  document.getElementById('specPanelTheoryTitle').innerHTML = 'Theory ('+theoryInSpec.length+')';
  document.getElementById('specPanelTheoryBody').innerHTML = theoryInSpec.map(function(n){
    return '<button class="doc-card" data-theory-note="'+escapeHtml(n.id)+'">'+
      '<div class="doc-stripe" style="background:var(--accent)"></div>'+
      '<div class="doc-inner">'+
        '<div class="doc-top"><span class="type-tag">'+escapeHtml(n.system||'Note')+'</span>'+(n.subtopic && n.subtopic!=='General' ? '<span class="theory-sub-tag">'+escapeHtml(n.subtopic)+'</span>':'')+'</div>'+
        '<p class="doc-title">'+escapeHtml(n.title)+'</p>'+
        '<p class="doc-snippet">'+escapeHtml(String(n.md||'').replace(/\s+/g,' ').substring(0,110))+'</p>'+
      '</div>'+
    '</button>';
  }).join('') || '<p style="color:var(--ink-muted);padding:11px 4px">No theory notes for this specialty yet.</p>';
  document.getElementById('specPanelTheory').classList.remove('open');

  document.getElementById('specPanelFlashcards').style.display = allFlashcardDecks.length ? '' : 'none';
  document.getElementById('specPanelFlashcardsTitle').innerHTML = 'Flashcards ('+decksInSpec.length+')';
  document.getElementById('specPanelFlashcardsBody').innerHTML = decksInSpec.map(function(d){
    var snip = (d.subtopics||[]).length ? (d.subtopics||[]).slice(0,4).join(' · ') : d.cards.map(function(c){ return c.subtopic; }).slice(0,3).join(' · ');
    return '<button class="doc-card" data-theory-deck="'+escapeHtml(d.id)+'">'+
      '<div class="doc-stripe" style="background:var('+_theorySpecVar(d.specialty)+')"></div>'+
      '<div class="doc-inner">'+
        '<div class="doc-top">'+_theoryPill(d.specialty, d.specialty)+'<span class="type-tag">'+d.cards.length+' card'+(d.cards.length===1?'':'s')+'</span></div>'+
        '<p class="doc-title">'+escapeHtml(d.title)+'</p>'+
        '<p class="doc-snippet">'+escapeHtml(snip)+'</p>'+
      '</div>'+
    '</button>';
  }).join('') || '<p style="color:var(--ink-muted);padding:11px 4px">No flashcard decks for this specialty yet.</p>';
  document.getElementById('specPanelFlashcards').classList.remove('open');

  document.getElementById('specPanelPearlsTitle').innerHTML = 'Pearls ('+pearlsInSpec.length+')';
  var specV = SPEC_VAR[name] || '--spec-other';
  document.getElementById('specPanelPearlsBody').innerHTML = pearlsInSpec.map(function(p){
    return '<div class="pearl-row" style="cursor:pointer;display:block;padding:11px 4px;border-bottom:1px solid var(--border)" data-open-pearl="'+p.id+'">'+
      '<div style="margin-bottom:4px;font-size:.88rem;line-height:1.4">'+escapeHtml(p.pearl||'')+'</div>'+
      '<div style="font-size:.7rem;color:var('+specV+');opacity:.85">'+escapeHtml(p.source_paper||'')+'</div>'+
    '</div>';
  }).join('') || '<p style="color:var(--ink-muted);padding:11px 4px">No pearls for this specialty yet.</p>';
  document.getElementById('specPanelPearls').classList.remove('open');

  renderSpecialtySubtopicChips(name);
}

function renderSpecialtySubtopicChips(name){
  var subtopics = SUBTOPIC_MAP[name] || [];
  var chipsHTML = '<button class="subtopic-chip-clear" data-subtopic-clear>Clear all</button>';
  subtopics.forEach(function(st){
    var paperCount = baseDataset.filter(function(p){ return normalizeSpec(p.system)===name && (p.subtopic||p.system)===st && p.type.toLowerCase()!=='guideline'; }).length;
    var guidelineCount = baseDataset.filter(function(p){ return normalizeSpec(p.system)===name && (p.subtopic||p.system)===st && p.type.toLowerCase()==='guideline'; }).length;
    var pearlCount = allPearls.filter(function(p){ return normalizeSpec(p.system)===name && (p.subtopic||p.system)===st; }).length;
    var theoryCount = THEORY_NOTES.filter(function(n){ return normalizeSpec(n.system)===name && (n.subtopic||'General')===st; }).length;
    var deckCount = allFlashcardDecks.filter(function(d){ return normalizeSpec(d.specialty)===name && (d.id===name+'/'+st || (d.subtopics||[]).indexOf(st)>=0); }).length;
    var active = activeSubtopic===st ? ' active' : '';
    chipsHTML += '<button class="subtopic-chip'+active+'" data-subtopic="'+st+'">'+st+' <span style="opacity:.6">'+paperCount+'p '+guidelineCount+'g '+(theoryCount?theoryCount+'t ':'')+(deckCount?deckCount+'f ':'')+pearlCount+'&#9679;</span></button>';
  });
  document.getElementById('specSubtopicChips').innerHTML = chipsHTML;
}

// =====================================================================
// PEARLS
// =====================================================================
function renderPearlChips(){
  var pearlCounts = {};
  allPearls.forEach(function(p){ var sys=normalizeSpec(p.system||'Other'); pearlCounts[sys]=(pearlCounts[sys]||0)+1; });
  var chipsHTML = SPECS.map(function(s){
    var count = pearlCounts[s.name]||0;
    var active = activePearlSpecs.has(s.name);
    return '<button class="chip '+(active?'active':'')+'" data-pearl-chip="'+s.name+'" style="--chip-color:var('+s.var+')"><span class="dot" style="background:'+(active?'currentColor':'var('+s.var+')')+'"></span>'+s.name+' ('+count+')</button>';
  }).join('');
  document.getElementById('pearlChips').innerHTML = chipsHTML + '<button class="chip" data-pearl-chip-reset>Reset</button><button class="chip" data-pearl-chip-uncheck>Uncheck all</button>';
}

function renderPearls(){
  var q = (document.getElementById('pearlsSearch').value || '').toLowerCase().trim();
  var sortVal = document.getElementById('pearlsSort').value;
  var filtered = allPearls.filter(function(p){
    return activePearlSpecs.has(normalizeSpec(p.system)) && (q==='' || (p.pearl||'').toLowerCase().indexOf(q)!==-1);
  });
  if(sortVal==='newest') {
    filtered = [].concat(filtered).sort(function(a,b){ return parseInt(b.id||0) - parseInt(a.id||0); });
  } else {
    filtered = [].concat(filtered).sort(function(a,b){ return parseInt(a.id||0) - parseInt(b.id||0); });
  }
  _currentPearlList = filtered;
  var shown = filtered.slice(0, pearlsShown);
  var noPearlsHTML = emptyStateHTML('pearls');
  if(activePearlSpecs.size===0){ noPearlsHTML = '<p style="color:var(--ink-muted);text-align:center;padding:20px">Select a specialty above to see pearls.</p>'; }
  document.getElementById('pearlsList').innerHTML = shown.map(function(p){
    var sysNorm = normalizeSpec(p.system);
    var v = SPEC_VAR[sysNorm] || '--spec-other';
    return '<button class="pearl-row" data-open-pearl="'+p.id+'">'+
      '<span class="dot" style="background:var('+v+')"></span>'+
      '<span class="txt">'+escapeHtml((p.pearl||'').substring(0,150))+(p.pearl&&p.pearl.length>150?'&hellip;':'')+'<span class="src">'+sysNorm+' &middot; '+(p.source_paper||'Clinical pearl')+'</span></span>'+
    '</button>';
  }).join('') || noPearlsHTML;
  document.getElementById('pearlsCount').textContent = 'Showing '+shown.length+' of '+filtered.length+' pearls';
  document.getElementById('loadMorePearls').style.display = shown.length < filtered.length ? 'inline-flex' : 'none';
}

// =====================================================================
// SERENDIPITY MODE
// =====================================================================
function loadSerendipityHistory() {
  try {
    var stored = localStorage.getItem('hackccm_serendipity_history');
    if (stored) _serendipityHistory = JSON.parse(stored);
  } catch (e) { _serendipityHistory = []; }
}

function saveSerendipityHistory() {
  try {
    localStorage.setItem('hackccm_serendipity_history', JSON.stringify(_serendipityHistory));
  } catch (e) {}
}

function openSerendipityModal() {
  var specs = SPECS.map(function(s) {
    var count = allPearls.filter(function(p) { return normalizeSpec(p.system) === s.name; }).length;
    return '<label><input type="checkbox" value="' + s.name + '"> ' + s.name + ' (' + count + ')</label>';
  }).join('');
  document.getElementById('serendipitySpecialties').innerHTML = specs;
  updateSerendipitySpecCount();
  document.getElementById('serendipityModal').style.display = 'flex';
  document.body.classList.add('modal-open');
}

function closeSerendipityModal() {
  document.getElementById('serendipityModal').style.display = 'none';
  document.body.classList.remove('modal-open');
}

function updateSerendipitySpecCount() {
  var checked = document.querySelectorAll('#serendipitySpecialties input:checked').length;
  document.getElementById('serendipitySpecCount').textContent = '(' + checked + ' selected)';
}

function selectAllSerendipitySpecialties() {
  document.querySelectorAll('#serendipitySpecialties input').forEach(function(cb) { cb.checked = true; });
  updateSerendipitySpecCount();
}

function clearAllSerendipitySpecialties() {
  document.querySelectorAll('#serendipitySpecialties input').forEach(function(cb) { cb.checked = false; });
  updateSerendipitySpecCount();
}

function resetSerendipityHistory() {
  if (confirm('Clear serendipity history? This will allow previously shown pearls to appear again.')) {
    _serendipityHistory = [];
    saveSerendipityHistory();
    showToast('History reset');
  }
}

function startSerendipity() {
  var count = parseInt(document.querySelector('input[name="serendipityCount"]:checked').value, 10);
  var specialties = Array.from(document.querySelectorAll('#serendipitySpecialties input:checked')).map(function(cb) { return cb.value; });

  if (specialties.length === 0) {
    showToast('Select at least one specialty');
    return;
  }

  var pool = allPearls.filter(function(p) {
    return specialties.includes(normalizeSpec(p.system)) && !_serendipityHistory.includes(String(p.id));
  });

  if (pool.length === 0) {
    showToast('No new pearls available for selected specialties');
    return;
  }

  pool.sort(function() { return Math.random() - 0.5; });
  _serendipityPearls = pool.slice(0, count);
  _serendipityIndex = 0;
  _serendipityMode = true;

  _serendipityPearls.forEach(function(p) { _serendipityHistory.push(String(p.id)); });
  saveSerendipityHistory();

  closeSerendipityModal();
  openReader(_serendipityPearls[0], 'pearl');
}

function navigateSerendipity(direction) {
  if (!_serendipityMode || _serendipityPearls.length === 0) return;
  var step = direction === 'next' ? 1 : -1;
  var targetIdx = _serendipityIndex + step;
  if (targetIdx >= 0 && targetIdx < _serendipityPearls.length) {
    _serendipityIndex = targetIdx;
    openReader(_serendipityPearls[_serendipityIndex], 'pearl');
  }
}

// =====================================================================
// READER
// =====================================================================
function openReader(entry, kind){
  if (!entry) return;
  navPushState('reader');
  var entrySysNorm = normalizeSpec(entry.system);
  var v = SPEC_VAR[entrySysNorm] || '--spec-other';
  var body = document.getElementById('readerBody');
  body.scrollTop = 0;
  document.getElementById('readerProgress').style.width = '0%';

if(kind==='pearl'){
    _currentPearlIndex = _currentPearlList.findIndex(function(p){ return String(p.id)===String(entry.id); });
    var idx = _currentPearlIndex;
    var isSerendipity = _serendipityMode && _serendipityPearls.length > 0;
    var prevBtn, nextBtn, navRow;
    if (isSerendipity) {
      prevBtn = _serendipityIndex > 0 ? '<button class="btn nav-btn" data-serendipity-nav="prev">&#9664; Previous</button>' : '';
      nextBtn = _serendipityIndex < _serendipityPearls.length - 1 ? '<button class="btn nav-btn" data-serendipity-nav="next">Next &#9654;</button>' : '';
      var progress = '<span class="serendipity-progress">Pearl ' + (_serendipityIndex + 1) + ' of ' + _serendipityPearls.length + '</span>';
      navRow = (prevBtn||nextBtn) ? '<div class="reader-nav">' + progress + prevBtn + nextBtn + '</div>' : '';
    } else {
      prevBtn = idx>0 ? '<button class="btn nav-btn" data-pearl-nav="prev">&#9664; Previous</button>' : '';
      nextBtn = idx>=0 && idx<_currentPearlList.length-1 ? '<button class="btn nav-btn" data-pearl-nav="next">Next &#9654;</button>' : '';
      var hasPrintablePaper = entry.file_name && baseDataset.some(function(d){ return d.file_name === entry.file_name.replace(/\.json$/, '.pdf'); });
      var articleBtn = hasPrintablePaper ? '<button class="btn nav-btn" data-open-pearl-article="'+entry.id+'">&#128196; Open article</button>' : '';
      navRow = (prevBtn||nextBtn||articleBtn) ? '<div class="reader-nav">'+articleBtn+prevBtn+nextBtn+'</div>' : '';
    }
    var pbmRef = 'pearl:'+entry.id;
    registerBookmarkMeta(pbmRef, {kind:'pearl', title: entry.pearl || entry.source_paper || 'Clinical pearl', system: entry.system || 'General', type: entry.type || 'Pearl', locator: {id: entry.id}});
    body.innerHTML = ''+
      pillHTML(entrySysNorm||'General', (entrySysNorm||'General')+' &middot; Pearl')+
      '<h2 style="font-size:1.15rem;line-height:1.4">"'+escapeHtml(entry.pearl||'')+'"</h2>'+
      '<p class="meta">'+(entry.source_paper||'Clinical pearl')+'</p>'+
      '<div class="reader-actions">'+bookmarkBtnHTML(pbmRef)+(entry.file_name?'<button class="related-btn" data-open-related="paper:'+escapeHtml(entry.file_name.replace(/\.json$/i,'.pdf'))+'" title="Related papers, guidelines, theory notes, decks & pearls">&#128279; Related</button>':'')+'</div>'+
      navRow;
    document.body.classList.add('reader-open');
    return;
  }

  // Paper
  body.innerHTML = '<div class="reader-loading"><p>&#128270; Loading summary&hellip;</p></div>';
  document.body.classList.add('reader-open');

  var file_name = encodeURIComponent(entry.file_name || '');
  var system = encodeURIComponent(entry.system || 'General');
  var type = encodeURIComponent(entry.type || 'Other');
  fetch('/api/summary?file_name='+file_name+'&system='+system+'&type='+type)
    .then(function(r){ return r.json(); })
    .then(function(data){
      if(data.error){ body.innerHTML = '<div class="reader-loading"><p>&#9888;&#65039; Could not load summary.</p></div>'; return; }
      var content = data.content || '';
      var authors = data.authors || 'Unknown Authors';
      var doiHTML = (entry.doi && entry.doi!=='#') ? '<a href="'+entry.doi+'" target="_blank" class="btn" style="font-size:.76rem;padding:5px 10px;display:inline-block;border:1px solid var(--border);border-radius:6px;">&#128279; Source</a>' : '';
      var rendered = marked.parse(content);
      var collapsible = makeCollapsible(rendered);

      // Build evidence rows from recommendations if present
      var evidenceHTML = '';
      if(data.recommendations && data.recommendations.length) {
        evidenceHTML = '<h4 class="evidence-head">Key evidence</h4>';
        data.recommendations.forEach(function(block){
          if(block.recommendations) {
            block.recommendations.forEach(function(rec){
              var stat = rec.strength ? rec.strength : '';
              if(rec.evidence_grade) stat = stat + (stat ? ' ' : '') + rec.evidence_grade;
              var label = rec.statement ? rec.statement : '';
              if(rec.rec_id) label = '['+rec.rec_id+'] '+label;
              evidenceHTML += '<div class="evidence-row"><div class="evidence-statement">'+marked.parse(label)+'</div>'+(stat?'<div class="evidence-stat">'+escapeHtml(stat)+'</div>':'')+'</div>';
            });
          }
        });
      }

      // Build pearl box
      var pearlBoxHTML = '';
      if(data.key_pearls && data.key_pearls.length) {
        pearlBoxHTML = '<div class="pearl-box"><strong>Key pearl &mdash;</strong> '+escapeHtml(data.key_pearls[0])+'</div>';
      }

      var bmKind = (entry.type||'').toLowerCase()==='guideline' ? 'guideline' : 'paper';
      var bmRef = bmKind + ':' + (entry.file_name || '');
      registerBookmarkMeta(bmRef, {kind: bmKind, title: entry.title, system: entry.system || 'General', type: entry.type || 'Other', locator: {file_name: entry.file_name || '', system: entry.system || 'General', type: entry.type || 'Other'}});
      body.innerHTML = ''+
        pillHTML(entry.system, entry.system+' &middot; '+entry.type)+
        '<h2>'+escapeHtml(entry.title)+'</h2>'+
        '<p class="meta">'+(authors!=='Unknown Authors'?'&mdash; '+escapeHtml(authors)+' &middot; ':'')+ (entry.journal||'')+'</p>'+
        '<div class="reader-actions">'+doiHTML+'<button class="related-btn" data-open-related="paper:'+escapeHtml(entry.file_name||'')+'" title="Related papers, guidelines, theory notes, decks &amp; pearls">&#128279; Related</button>'+bookmarkBtnHTML(bmRef)+exportPaperBtnHTML(entry)+'</div>'+
        pearlBoxHTML+
        collapsible+
        evidenceHTML;
      katexify(body);
    })
    .catch(function(){
      body.innerHTML = '<div class="reader-loading"><p>&#10060; Network error.</p></div>';
    });
}

function closeReader(){ document.body.classList.remove('reader-open'); }

// =====================================================================
// RELATED CONTENT PANEL (cross-linking)
// =====================================================================
var _relatedSourceId = null;
var _relatedList = [];
var _relatedActiveReason = '';

function relatedEntityById(id){
  var e = RELATED_CATALOG.find(function(x){ return x.id===id; });
  return e || {id:id, kind:'', system:'', type:'', subtopic:'', title:id, tags:[]};
}

function openRelatedPanel(id){
  if(!RELATED_META.loaded){
    document.getElementById('relatedOverlayTitle').textContent = 'Related content';
    document.getElementById('relatedMeta').textContent = '';
    document.getElementById('relatedReasonBar').innerHTML = '';
    document.getElementById('relatedScroll').innerHTML = '<div class="related-empty">No related links built yet &mdash; run <b>python acumen_core/linker.py</b> to generate the cross-link index.</div>';
    document.getElementById('relatedOverlay').classList.add('open');
    document.body.classList.add('related-open');
    return;
  }
  var source = relatedEntityById(id || '');
  _relatedSourceId = id || '';
  _relatedList = (RELATED_INDEX[id || ''] || []).slice();
  document.getElementById('relatedOverlayTitle').textContent = source.title || 'Related content';
  document.getElementById('relatedMeta').innerHTML = '<span style="color:var(--ink-muted);font-size:.72rem">Cross-linked by topic'+( _relatedList.length ? ' &middot; '+_relatedList.length+' items' : '')+'</span>';
  renderRelatedReasonBar();
  renderRelatedRows();
  document.getElementById('relatedOverlay').classList.add('open');
  document.body.classList.add('related-open');
}

function renderRelatedReasonBar(){
  var counts = {};
  _relatedList.forEach(function(l){ var r = l.reason || 'same topic'; counts[r]=(counts[r]||0)+1; });
  var reasons = Object.keys(counts).sort();
  var html = '<button class="related-reason-chip'+(''===_relatedActiveReason?' active':'')+'" data-related-reason="">All ('+_relatedList.length+')</button>';
  reasons.forEach(function(r){
    html += '<button class="related-reason-chip'+(_relatedActiveReason===r?' active':'')+'" data-related-reason="'+escapeHtml(r)+'">'+escapeHtml(r)+' ('+counts[r]+')</button>';
  });
  document.getElementById('relatedReasonBar').innerHTML = html;
}

function renderRelatedRows(){
  var filtered = _relatedActiveReason ? _relatedList.filter(function(r){ return (r.reason||'same topic')===_relatedActiveReason; }) : _relatedList;
  var el = document.getElementById('relatedScroll');
  if(!filtered.length){
    el.innerHTML = '<div class="related-empty">'+( _relatedActiveReason ? 'No items with reason &ldquo;'+escapeHtml(_relatedActiveReason)+'&rdquo;.' : 'No related content for this item yet.')+'</div>';
    return;
  }
  var groups = { papers:[], theory:[], decks:[] };
  filtered.forEach(function(r){
    var e = relatedEntityById(r.to);
    if(!e.kind) return;
    if(e.kind==='paper'||e.kind==='guideline') groups.papers.push({r:r, e:e});
    else if(e.kind==='theory') groups.theory.push({r:r, e:e});
    else if(e.kind==='flashcard_deck') groups.decks.push({r:r, e:e});
  });
  var html = '';
  function addGroup(items, label){
    if(!items.length) return;
    html += '<div class="related-group-label">'+label+'</div>';
    items.sort(function(a,b){ return (b.r.weight||0)-(a.r.weight||0); });
    items.forEach(function(it){
      var kindLabel = it.e.kind==='guideline' ? 'Guideline' : (it.e.kind==='theory' ? 'Theory' : (it.e.kind==='flashcard_deck' ? 'Deck' : 'Paper'));
      html += '<button class="related-row" data-related-go="'+escapeHtml(it.e.id)+'">'+
        '<span class="related-row-top">'+
          '<span class="related-kind">'+kindLabel+'</span>'+
          '<span class="related-title">'+escapeHtml(it.e.title||it.e.id)+'</span>'+
        '</span>'+
        '<span class="related-reason">'+escapeHtml(it.r.reason||'')+'</span>'+
      '</button>';
    });
  }
  addGroup(groups.papers, 'Papers &amp; Guidelines');
  addGroup(groups.theory, 'Theory Notes');
  addGroup(groups.decks, 'Flashcard Decks');

  // Pearls nested under related papers (pearl → parent paper is a free link)
  var allFns = [];
  var source = relatedEntityById(_relatedSourceId);
  if(source && (source.kind==='paper'||source.kind==='guideline')) allFns.push(source.id.replace(/^paper:/,''));
  groups.papers.forEach(function(it){ allFns.push(it.e.id.replace(/^paper:/,'')); });
  var pearlN = [];
  var seenPearls = {};
  allFns.forEach(function(fn){
    if(!fn) return;
    var paperPearls = allPearls.filter(function(p){ return relatedPearlPaper(p)===fn; });
    if(!paperPearls.length) return;
    var paper = baseDataset.find(function(d){ return d.file_name===fn; });
    var pTitle = paper ? paper.title : fn;
    paperPearls.slice(0,12).forEach(function(p){
      if(seenPearls[p.id]) return;
      seenPearls[p.id] = true;
      pearlN.push({
        pearl: p.pearl || '',
        id: p.id,
        source: pTitle
      });
    });
  });
  if(pearlN.length){
    html += '<div class="related-group-label">Pearls</div>';
    pearlN.slice(0,40).forEach(function(p){
      html += '<button class="related-row" data-related-pearl="'+escapeHtml(p.id)+'">'+
        '<span class="related-kind">Pearl</span>'+
        '<span class="related-title">'+escapeHtml((p.pearl||'').substring(0,140))+(p.pearl&&p.pearl.length>140?'&hellip;':'')+'</span>'+
        '<span class="related-reason">'+escapeHtml(p.source.substring(0,28))+'</span>'+
      '</button>';
    });
  }
  el.innerHTML = html;
}

function relatedPearlPaper(p){
  var fn = String(p.file_name || '').trim();
  if(fn) return fn.replace(/\.json$/i, '.pdf');
  return '';
}

function closeRelatedPanel(){
  document.getElementById('relatedOverlay').classList.remove('open');
  document.body.classList.remove('related-open');
  _relatedSourceId = null;
  _relatedList = [];
}

function relatedGoTo(id){
  var e = relatedEntityById(id);
  closeRelatedPanel();
  if(e.kind==='paper'||e.kind==='guideline'){
    var fn = id.replace(/^paper:/, '');
    var target = baseDataset.find(function(d){ return d.file_name===fn; });
    if(target) openReader(target, 'paper');
    return;
  }
  if(e.kind==='theory'){
    var rel = id.replace(/^theory:/, '');
    var fn = rel.split('/').pop();
    var note = THEORY_NOTES.find(function(n){ return n.id===fn; }) || THEORY_NOTES.find(function(n){ return n.rel===rel; });
    if(note) openTheoryNote(note.id);
    return;
  }
  if(e.kind==='flashcard_deck'){
    openTheoryDeck(id.replace(/^deck:/, ''), 0);
    return;
  }
}

function makeCollapsible(html){
  var parts = html.split(/(<h2[^>]*>[\s\S]*?<\/h2>)/i);
  if(parts.length<2) return html;
  var r = ''; if(parts[0].trim()) r += '<div>'+parts[0]+'</div>';
  var first = true;
  for(var i=1;i<parts.length;i+=2){
    var h = parts[i], c = parts[i+1]||'', m = h.match(/>([^<]*)</), t = m ? m[1] : 'Section';
    r += '<details class="summary-section"'+(first?' open':'')+'><summary class="summary-heading">'+t+'</summary><div class="summary-content">'+c.replace(h,'')+'</div></details>';
    first = false;
  }
  return r;
}

// =====================================================================
// SEARCH OVERLAY
// =====================================================================
function openSearch(){
  document.body.classList.add('search-open');
  var input = document.getElementById('globalSearchInput');
  input.value = '';
  renderSearchResults('');
  setTimeout(function(){ input.focus(); }, 60);
}
function closeSearch(){ document.body.classList.remove('search-open'); }
function renderSearchResults(qRaw){
  var q = (qRaw||'').toLowerCase().trim();
  var box = document.getElementById('searchResults');
  if(q===''){ box.innerHTML = '<div class="search-empty">Try &ldquo;troponin&rdquo;, &ldquo;pip-tazo&rdquo;, &ldquo;KDIGO&rdquo;, or a specialty name.</div>'; return; }
  var pMatches = baseDataset.filter(function(p){ return p.title.toLowerCase().indexOf(q)!==-1; }).slice(0,5);
  var plMatches = allPearls.filter(function(p){ return (p.pearl||'').toLowerCase().indexOf(q)!==-1; }).slice(0,5);
  var ctMatches = CONDENSED_INDEX.filter(function(t){
    return t.trial_name.toLowerCase().indexOf(q)!==-1
        || (t.one_liner||'').toLowerCase().indexOf(q)!==-1
        || (t.keywords_str||'').toLowerCase().indexOf(q)!==-1
        || t.system.toLowerCase().indexOf(q)!==-1;
  }).slice(0,5);
  var esMatches = TRIAL_INDEX.filter(function(t){
    return (t.trial_name||'').toLowerCase().indexOf(q)!==-1
        || (t.one_liner||'').toLowerCase().indexOf(q)!==-1
        || (t.specialty||'').toLowerCase().indexOf(q)!==-1;
  }).slice(0,5);
  var fcMatches = [];
  var theoryCardsSearched = 0;
  allFlashcardDecks.forEach(function(d){
    d.cards.forEach(function(c){
      var hay = (c.subtopic+' '+(c.front||'')+' '+(c.back||'')+' '+(c.tags||[]).join(' ')+' '+d.specialty+' '+d.title).toLowerCase();
      if(hay.indexOf(q)!==-1 && theoryCardsSearched<6){
        theoryCardsSearched++;
        fcMatches.push({cardId: c.id, deckId: d.id, label: (c.front||c.subtopic||c.id).substring(0,90), system: d.specialty});
      }
    });
  });
  var ntMatches = THEORY_NOTES.filter(function(n){
    return (n.title+' '+n.md).toLowerCase().indexOf(q)!==-1;
  }).slice(0,5);
  var total = pMatches.length + plMatches.length + ctMatches.length + esMatches.length + fcMatches.length + ntMatches.length;
  if(!total){ box.innerHTML = '<div class="search-empty">No results for &ldquo;'+qRaw+'&rdquo;.</div>'; return; }
  var html = '';
  if(pMatches.length) html += '<div class="search-group-label">Papers &amp; guidelines ('+pMatches.length+')</div>' + pMatches.map(function(p){ return '<button class="search-result" data-open-paper="'+p.id+'" data-close-search>'+escapeHtml(p.title)+'</button>'; }).join('');
  if(plMatches.length) html += '<div class="search-group-label">Pearls ('+plMatches.length+')</div>' + plMatches.map(function(p){ return '<button class="search-result" data-open-pearl="'+p.id+'" data-close-search>'+escapeHtml((p.pearl||'').substring(0,80))+'</button>'; }).join('');
  if(ctMatches.length) html += '<div class="search-group-label">Core Critical Care Trials ('+ctMatches.length+')</div>' + ctMatches.map(function(t){ return '<button class="search-result" data-open-condensed="'+t.system+'/'+t.name+'" data-close-search>'+escapeHtml(t.trial_name)+'</button>'; }).join('');
  if(esMatches.length) html += '<div class="search-group-label">ESBICM Landmark Trials ('+esMatches.length+')</div>' + esMatches.map(function(t){ return '<button class="search-result" data-open-trial="'+t.slug+'" data-close-search>'+escapeHtml(t.trial_name||'')+' &middot; '+escapeHtml(t.specialty||'')+'</button>'; }).join('');
  if(fcMatches.length) html += '<div class="search-group-label">Flashcards ('+fcMatches.length+')</div>' + fcMatches.map(function(f){ return '<button class="search-result" data-theory-card="'+f.cardId+'" data-close-search>'+escapeHtml(f.label)+' &middot; '+escapeHtml(f.system)+'</button>'; }).join('');
  if(ntMatches.length) html += '<div class="search-group-label">Theory Topics ('+ntMatches.length+')</div>' + ntMatches.map(function(n){ return '<button class="search-result" data-theory-note="'+escapeHtml(n.id)+'" data-close-search>'+escapeHtml(n.title)+'</button>'; }).join('');
  box.innerHTML = html;
}

// =====================================================================
// DRAWER / SHEET
// =====================================================================
function openDrawer(){ document.body.classList.add('drawer-open'); }
function closeDrawer(){ document.body.classList.remove('drawer-open'); }
function openSheet(){ document.body.classList.add('sheet-open'); }
function closeSheet(){ document.body.classList.remove('sheet-open'); }

// =====================================================================
// THEME / FONT
// =====================================================================
var THEMES = ['light','dim','dark'];
var THEME_GLYPH = {light:'&#9728;', dim:'&#9712;', dark:'&#9790;'};
function setTheme(t){
  document.documentElement.setAttribute('data-theme', t);
  var tb = document.getElementById('themeBtn');
  if(tb) tb.innerHTML = THEME_GLYPH[t] || '&#9712;';
  document.querySelectorAll('#themeChips .chip').forEach(function(c){ c.classList.toggle('active', c.dataset.themeChoice===t); });
  try { localStorage.setItem('hackccm_theme', t); } catch(e){}
}
function setSiteFontSize(px){
  document.body.style.setProperty('--site-fs', px + 'px');
  document.querySelectorAll('#fontChips .chip').forEach(function(c){ c.classList.toggle('active', c.dataset.fontPx===String(px)); });
  try { localStorage.setItem('hackccm_fontSize', String(px)); } catch(e){}
}
function showToast(msg){
  var t = document.getElementById('toast');
  t.innerHTML = msg;
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(function(){ t.classList.remove('show'); }, 2400);
}

function escapeHtml(str){
  if(!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function capitalizeFirst(str){
  if(!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function renderListItem(v){
  if(typeof v === 'string') return '<li>'+escapeHtml(v)+'</li>';
  if(v && typeof v === 'object'){
    if(v.domain && v.notes) return '<li><strong>'+escapeHtml(v.domain)+':</strong> '+escapeHtml(v.notes)+'</li>';
    if(v.topic && v.notes) return '<li><strong>'+escapeHtml(v.topic)+':</strong> '+escapeHtml(v.notes)+'</li>';
    if(v.trial && v.relation) return '<li><strong>'+escapeHtml(v.trial)+':</strong> '+escapeHtml(v.relation)+'</li>';
    return '<li>'+escapeHtml(JSON.stringify(v))+'</li>';
  }
  return '<li>'+escapeHtml(String(v))+'</li>';
}

// =====================================================================
// TRIALS
// =====================================================================
function renderTrials(){
  // My Trials placeholder is static HTML
  // ESBICM hero card is static HTML
}

function renderESBICM(){
  var container = document.getElementById('trialsEsbicmResults');
  var spec = document.getElementById('trialFilterSpecialty').value;
  var res = document.getElementById('trialFilterResult').value;
  var typ = document.getElementById('trialFilterType').value;
  var hasFilter = spec || res || typ;

  if(!hasFilter){
    // Show specialty grid
    var html = '<div class="trials-spec-grid">';
    TRIAL_SPECS.forEach(function(s){
      var c = TRIAL_SPEC_COUNTS[s] || 0;
      var v = TRIAL_SPEC_VAR[s] || '--tspec-general';
      html += '<button class="trials-spec-tile" style="--tile-color:var('+v+')" data-trial-spec="'+s+'" role="button">'+
        '<div class="dot" style="background:var('+v+')"></div>'+
        '<div style="font-weight:700;font-size:.9rem">'+s+'</div>'+
        '<div class="count">'+c+' trial'+(c!==1?'s':'')+'</div>'+
        '</button>';
    });
    html += '</div>';
    container.innerHTML = html;
    return;
  }

  // Filtered: fetch from API
  var params = new URLSearchParams({specialty:spec, result_category:res, trial_type:typ, page:1, limit:300});
  fetch('/api/trials?'+params.toString())
    .then(function(r){ return r.json(); })
    .then(function(data){
      var list = data.trials || [];
      _currentTrialList = list;
      if(!list.length){
        container.innerHTML = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials match your filters.</p></div>';
        return;
      }
      var html = '<p style="font-size:.82rem;color:var(--ink-muted);margin-bottom:10px">'+list.length+' trial'+(list.length!==1?'s':'')+' found</p>';
      list.forEach(function(t, i){
        html += renderTrialCard(t, i);
      });
      container.innerHTML = html;
    });
}

function renderTrialCard(t, idx){
  var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
  var resColor = 'neu';
  if(resClass.indexOf('pos')>=0) resColor = 'pos';
  else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
  else if(resClass.indexOf('neg')>=0) resColor = 'neg';
  return '<div class="trial-card" data-open-trial="'+t.slug+'" data-idx="'+idx+'" role="button" tabindex="0">'+
    '<h4>'+escapeHtml(t.trial_name)+'</h4>'+
    '<p class="one-liner">'+escapeHtml(t.one_liner||'')+'</p>'+
    '<div class="meta-row">'+
      '<span class="badge">'+escapeHtml(t.trial_type||'')+'</span>'+
      '<span class="result-badge '+resColor+'">'+escapeHtml(t.result_category||'')+'</span>'+
      (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
      '<span class="badge">'+t.year+'</span>'+
    '</div>'+
    '</div>';
}

function renderTrialsSpecialty(name){
  navPushState('trials-specialty');
  showView('trials-specialty');
  document.getElementById('trialsSpecTitle').textContent = name;
  var dot = document.getElementById('trialsSpecDot');
  var v = TRIAL_SPEC_VAR[name] || '--tspec-general';
  dot.style.background = 'var('+v+')';

  // Subtopic chips
  var sts = TRIAL_SUBTOPIC_MAP[name] || ['General'];
  var chipHtml = '<button class="subtopic-chip active" data-st="">All</button>';
  sts.forEach(function(st){
    chipHtml += '<button class="subtopic-chip" data-st="'+escapeHtml(st)+'">'+escapeHtml(st)+'</button>';
  });
  document.getElementById('trialsSubtopicChips').innerHTML = chipHtml;

  // Back button
  document.getElementById('trialsSpecBackBtn').onclick = function(){ history.back(); };

  _filterTrialsBySpecialty(name, '');
}

function _filterTrialsBySpecialty(name, subtopic){
  var filtered = TRIAL_INDEX.filter(function(t){
    if(t.specialty !== name) return false;
    if(subtopic && t.subtopic !== subtopic) return false;
    return true;
  });
  _currentTrialList = filtered;
  var html = '';
  filtered.forEach(function(t, i){
    html += renderTrialCard(t, i, filtered);
  });
  if(!html) html = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials in this category.</p></div>';
  document.getElementById('trialsSpecList').innerHTML = html;
}

function openTrialDetail(slug, list, idx){
  navPushState('trial-detail');
  showView('trial-detail');
  _currentTrialList = list || [];
  _currentTrialIdx = typeof idx === 'number' ? idx : -1;
  _currentTrialSlug = slug || '';

  var body = document.getElementById('trialDetailBody');
  body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--ink-muted)">Loading&hellip;</div>';

  fetch('/api/trial/'+slug)
    .then(function(r){ return r.json(); })
    .then(function(data){
      if(data.error){ body.innerHTML = '<div class="trial-empty"><span class="icon">&#9888;</span><p>Could not load trial.</p></div>'; return; }
      renderTrialDetailHTML(data, body);
    });
}

function renderTrialDetailHTML(data, body){
  // Credits bar
  var html = '<div class="trial-credits-bar">'+
    '<span class="trophy">&#127942;</span>'+
    '<span>Data sourced from <strong>ESBICM Trials Database</strong></span>'+
    '<span class="spacer"></span>'+
    '<button class="icon-btn-sm" onclick="openTrialOverlay(&#x27;trialCreditsOverlay&#x27;,&#x27;credits&#x27;)">&#127942; Credits</button>'+
    '<button class="icon-btn-sm" onclick="openTrialOverlay(&#x27;trialDisclaimerOverlay&#x27;,&#x27;disclaimer&#x27;)">&#8505;&#65039;</button>'+
    '</div>';

  // Title + journal
  html += '<h1>'+escapeHtml(data.trial_name || data.trial_title || '')+'</h1>';
  html += '<div class="trial-journal">';
  if(data.journal) html += escapeHtml(data.journal);
  if(data.year) html += ' &middot; '+data.year;
  if(data.doi){
    var doiUrl = data.doi;
    if(doiUrl && doiUrl!=='#' && !doiUrl.startsWith('http')) doiUrl = 'https://doi.org/'+doiUrl;
    if(doiUrl && doiUrl!=='#') html += ' &middot; <a href="'+doiUrl+'" target="_blank" rel="noopener" style="color:var(--accent)">&#128279; DOI</a>';
  }
  html += '</div>';
  registerBookmarkMeta('trial:'+_currentTrialSlug, {kind: 'trial', title: data.trial_name || data.trial_title || '', system: data.specialty || 'General', type: data.trial_type || '', locator: {slug: _currentTrialSlug}});
  html += '<div class="reader-actions" style="margin-top:10px">'+bookmarkBtnHTML('trial:'+_currentTrialSlug)+'</div>';

  // Meta strip
  html += '<div class="trial-meta-strip">';
  if(data.trial_type) html += '<span class="badge">'+escapeHtml(data.trial_type)+'</span>';
  if(data.result_category){
    var rc = data.result_category.toLowerCase().replace(/[^a-z]/g,'');
    var rcls = 'neu';
    if(rc.indexOf('pos')>=0) rcls = 'pos';
    else if(rc.indexOf('neg')>=0 && rc.indexOf('neu')>=0) rcls = 'negneu';
    else if(rc.indexOf('neg')>=0) rcls = 'neg';
    html += '<span class="result-badge '+rcls+'">'+escapeHtml(data.result_category)+'</span>';
  }
  if(data.sample_size) html += '<span class="badge">n='+data.sample_size+'</span>';
  if(data.evidence_level) html += '<span class="badge">&#11088; '+escapeHtml(data.evidence_level)+'</span>';
  html += '</div>';

  // One-liner
  if(data.one_liner) html += '<div class="trial-one-liner">'+escapeHtml(data.one_liner)+'</div>';

  // Sections as collapsible
  if(data.sections && data.sections.length){
    data.sections.forEach(function(s){
      var secContent = preprocessTrialContent(s.content || '');
      var secHtml = '<div class="trial-section"><details'+(s.id<=2?' open':'')+'><summary>'+escapeHtml(s.heading||'')+'</summary><div class="section-body">';
      if (typeof marked !== 'undefined' && marked.parse) {
        secHtml += marked.parse(secContent);
      } else {
        secHtml += '<p>'+secContent.replace(/\n/g, '<br>')+'</p>';
      }
      secHtml += '</div></details></div>';
      html += secHtml;
    });
  }

  // Prev/Next nav
  html += '<div class="trial-nav-bar">';
  if(_currentTrialIdx > 0 && _currentTrialList.length){
    var prev = _currentTrialList[_currentTrialIdx - 1];
    html += '<button class="btn nav-btn" onclick="openTrialDetail(&#x27;'+prev.slug+'&#x27;,_currentTrialList,'+(_currentTrialIdx-1)+')">&larr; '+escapeHtml(prev.toc_name||'Previous')+'</button>';
  }
  if(_currentTrialIdx >= 0 && _currentTrialIdx < _currentTrialList.length - 1){
    var next = _currentTrialList[_currentTrialIdx + 1];
    html += '<button class="btn nav-btn" onclick="openTrialDetail(&#x27;'+next.slug+'&#x27;,_currentTrialList,'+(_currentTrialIdx+1)+')">'+escapeHtml(next.toc_name||'Next')+' &rarr;</button>';
  }
  html += '</div>';

  body.innerHTML = html;
  katexify(body);
}

function preprocessTrialContent(text){
  if(!text) return '';
  // Convert bullet characters to markdown list syntax
  var out = text.replace(/^•\s*/gm, '- ').replace(/^o\s+/gm, '  - ');
  return out;
}

function filterTrials(){
  renderESBICM();
}

function clearTrialFilters(){
  document.getElementById('trialFilterSpecialty').value = '';
  document.getElementById('trialFilterResult').value = '';
  document.getElementById('trialFilterType').value = '';
  renderESBICM();
}

function openTrialOverlay(id, kind){
  document.getElementById(id).style.display = 'flex';
  if(kind==='credits'){
    var md = BOOT.credits_text;
    var html = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    document.getElementById('trialCreditsText').innerHTML = '<p>'+html+'</p>';
  }
  if(kind==='disclaimer'){
    var md = BOOT.trial_disclaimer_text;
    var html = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    document.getElementById('trialDisclaimerText').innerHTML = '<p>'+html+'</p>';
  }
}

function closeTrialOverlay(id){
  document.getElementById(id).style.display = 'none';
}

// =====================================================================
// CONDENSED TRIALS
// =====================================================================

function renderCondensedTrials(){
  var container = document.getElementById('condensedTrialsContent');
  var spec = document.getElementById('condensedFilterSpecialty').value;
  var res = document.getElementById('condensedFilterResult').value;
  var typ = document.getElementById('condensedFilterType').value;
  var hasFilter = spec || res || typ;

  if(!hasFilter){
    // Show specialty grid
    var html = '<div class="trials-spec-grid">';
    CONDENSED_SYSTEMS.forEach(function(s){
      var count = CONDENSED_INDEX.filter(function(t){ return t.system === s; }).length;
      var v = TRIAL_SPEC_VAR[s] || '--tspec-general';
      html += '<button class="trials-spec-tile" style="--tile-color:var('+v+')" data-condensed-spec="'+s+'" role="button">'+
        '<div class="dot" style="background:var('+v+')"></div>'+
        '<div style="font-weight:700;font-size:.9rem">'+s+'</div>'+
        '<div class="count">'+count+' trial'+(count!==1?'s':'')+'</div>'+
        '</button>';
    });
    html += '</div>';
    container.innerHTML = html;
    return;
  }

  // Filtered: show trial cards sorted by year descending
  var filtered = CONDENSED_INDEX.filter(function(t){
    if(spec && t.system !== spec) return false;
    if(res && t.result_category !== res) return false;
    if(typ && t.trial_type !== typ) return false;
    return true;
  }).sort(function(a,b){ return (b.year||0) - (a.year||0); });
  if(!filtered.length){
    container.innerHTML = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials match your filters.</p></div>';
    return;
  }
  var html = '<p style="font-size:.82rem;color:var(--ink-muted);margin-bottom:10px">'+filtered.length+' trial'+(filtered.length!==1?'s':'')+' found</p>';
  filtered.forEach(function(t, i){
    var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
    var resColor = 'neu';
    if(resClass.indexOf('pos')>=0) resColor = 'pos';
    else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
    else if(resClass.indexOf('neg')>=0) resColor = 'neg';
    html += '<div class="trial-card" data-open-condensed="'+t.system+'/'+t.name+'" data-idx="'+i+'" role="button" tabindex="0">'+
      '<h4>'+escapeHtml(t.trial_name || t.name.replace(/_/g,' '))+'</h4>'+
      '<p class="one-liner">'+escapeHtml(t.one_liner||'')+'</p>'+
      '<div class="meta-row">'+
        (t.trial_type ? '<span class="badge">'+escapeHtml(t.trial_type)+'</span>' : '')+
        (t.result_category ? '<span class="result-badge '+resColor+'">'+escapeHtml(t.result_category)+'</span>' : '')+
        (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
        (t.year ? '<span class="badge">'+t.year+'</span>' : '')+
      '</div>'+
      '</div>';
  });
  container.innerHTML = html;
}

function filterCondensed(){
  renderCondensedTrials();
}

function clearCondensedFilters(){
  document.getElementById('condensedFilterSpecialty').value = '';
  document.getElementById('condensedFilterResult').value = '';
  document.getElementById('condensedFilterType').value = '';
  renderCondensedTrials();
}

function renderCondensedSystem(name){
  navPushState('condensed-system');
  showView('condensed-system');
  document.getElementById('condensedSysTitle').textContent = name;
  var trials = CONDENSED_INDEX.filter(function(t){ return t.system === name; }).sort(function(a,b){ return (b.year||0) - (a.year||0); });
  var html = '';
  trials.forEach(function(t, i){
    var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
    var resColor = 'neu';
    if(resClass.indexOf('pos')>=0) resColor = 'pos';
    else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
    else if(resClass.indexOf('neg')>=0) resColor = 'neg';
    html += '<div class="trial-card" data-open-condensed="'+t.system+'/'+t.name+'" data-idx="'+i+'" role="button" tabindex="0">'+
      '<h4>'+escapeHtml(t.trial_name || t.name.replace(/_/g,' '))+'</h4>'+
      '<p class="one-liner">'+escapeHtml(t.one_liner||'')+'</p>'+
      '<div class="meta-row">'+
        (t.trial_type ? '<span class="badge">'+escapeHtml(t.trial_type)+'</span>' : '')+
        (t.result_category ? '<span class="result-badge '+resColor+'">'+escapeHtml(t.result_category)+'</span>' : '')+
        (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
        (t.year ? '<span class="badge">'+t.year+'</span>' : '')+
      '</div>'+
      '</div>';
  });
  if(!html) html = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials in this category.</p></div>';
  document.getElementById('condensedSysList').innerHTML = html;
}

function openCondensedTrialDetail(system, name){
  navPushState('condensed-detail');
  showView('condensed-detail');
  _currentCondensedRef = 'condensed:' + system + ':' + name;
  var body = document.getElementById('condensedDetailBody');
  body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--ink-muted)">Loading&hellip;</div>';
  document.getElementById('condensedDetailBackBtn').onclick = function(){ history.back(); };
  fetch('/api/condensed-trial/'+encodeURIComponent(system)+'/'+encodeURIComponent(name))
    .then(function(r){ return r.json(); })
    .then(function(data){
      if(data.error){ body.innerHTML = '<div class="trial-empty"><span class="icon">&#9888;</span><p>Could not load trial.</p></div>'; return; }
      renderCondensedDetailHTML(data, body);
    });
}

function renderCondensedDetailHTML(data, body){
  var html = '';

  // Title + journal
  html += '<h1>'+escapeHtml(data.trial_name || '')+'</h1>';
  html += '<div class="trial-journal">';
  if(data.journal) html += escapeHtml(data.journal);
  if(data.year) html += ' &middot; '+data.year;
  if(data.doi){
    var doiUrl = data.doi;
    if(doiUrl && doiUrl!=='#' && !doiUrl.startsWith('http')) doiUrl = 'https://doi.org/'+doiUrl;
    if(doiUrl && doiUrl!=='#') html += ' &middot; <a href="'+doiUrl+'" target="_blank" rel="noopener" style="color:var(--accent)">&#128279; DOI</a>';
  }
  html += '</div>';
  var cparts = String(_currentCondensedRef).split(':');
  var cSys = cparts[1] || 'General';
  var cName = cparts[2] || '';
  registerBookmarkMeta(_currentCondensedRef, {kind: 'condensed', title: data.trial_name || '', system: cSys, type: data.trial_type || '', locator: {system: cSys, name: cName}});
  html += '<div class="reader-actions" style="margin-top:10px">'+bookmarkBtnHTML(_currentCondensedRef)+'</div>';

  // Meta strip
  html += '<div class="trial-meta-strip">';
  if(data.trial_type) html += '<span class="badge">'+escapeHtml(data.trial_type)+'</span>';
  if(data.result_category){
    var rc = data.result_category.toLowerCase().replace(/[^a-z]/g,'');
    var rcls = 'neu';
    if(rc.indexOf('pos')>=0) rcls = 'pos';
    else if(rc.indexOf('neg')>=0 && rc.indexOf('neu')>=0) rcls = 'negneu';
    else if(rc.indexOf('neg')>=0) rcls = 'neg';
    html += '<span class="result-badge '+rcls+'">'+escapeHtml(data.result_category)+'</span>';
  }
  if(data.sample_size) html += '<span class="badge">n='+data.sample_size+'</span>';
  if(data.evidence_level) html += '<span class="badge">&#11088; '+escapeHtml(data.evidence_level)+'</span>';
  html += '</div>';

  // One-liner
  if(data.one_liner) html += '<div class="trial-one-liner">'+escapeHtml(data.one_liner)+'</div>';

  var sec = data.sections || {};

  // PICO card
  if(data.pico){
    html += '<div class="trial-section"><details open><summary>PICO</summary><div class="section-body"><table class="pico-table"><tr><th>Population</th><td>'+escapeHtml(data.pico.population||'')+'</td></tr><tr><th>Intervention</th><td>'+escapeHtml(data.pico.intervention||'')+'</td></tr><tr><th>Comparison</th><td>'+escapeHtml(data.pico.comparison||'')+'</td></tr><tr><th>Outcome</th><td>'+escapeHtml(data.pico.outcome||'')+'</td></tr></table></div></details></div>';
  }

  // Quick recall box
  if(sec.quick_recall){
    var qr = sec.quick_recall;
    html += '<div class="quick-recall-box">'+
      '<div class="qr-title">&#128161; Quick Recall</div>'+
      '<div class="qr-numbers">';
    if(qr.numbers_to_remember){
      qr.numbers_to_remember.forEach(function(n){ html += '<div class="qr-num">'+escapeHtml(n)+'</div>'; });
    }
    html += '</div>';
    if(qr.one_line_takeaway) html += '<div class="qr-takeaway">'+escapeHtml(qr.one_line_takeaway)+'</div>';
    html += '</div>';
  }

  // Clinical Summary (renamed from clinical_bottom_line)
  if(sec.clinical_bottom_line){
    var cbl = sec.clinical_bottom_line;
    html += '<div class="trial-section"><details open><summary>Clinical Summary</summary><div class="section-body">';
    if(cbl.verdict) html += '<p><strong>Verdict:</strong> '+escapeHtml(cbl.verdict)+'</p>';
    if(cbl.applies_to) html += '<p><strong>Applies to:</strong> '+escapeHtml(cbl.applies_to)+'</p>';
    if(cbl.does_not_mean) html += '<p><strong>Does not mean:</strong> '+escapeHtml(cbl.does_not_mean)+'</p>';
    if(cbl.implementation_caveats && cbl.implementation_caveats.length){
      html += '<p><strong>Implementation caveats:</strong></p><ul>';
      cbl.implementation_caveats.forEach(function(c){ html += '<li>'+escapeHtml(c)+'</li>'; });
      html += '</ul>';
    }
    html += '</div></details></div>';
  }

  // Critical Appraisal
  if(sec.critical_appraisal){
    var ca = sec.critical_appraisal;
    html += '<div class="trial-section"><details open><summary>Critical Appraisal</summary><div class="section-body">';
    if(ca.summary) html += '<p><strong>Summary:</strong> '+escapeHtml(ca.summary)+'</p>';
    if(ca.rating) html += '<p><strong>Rating:</strong> <span class="badge">'+escapeHtml(ca.rating)+'</span></p>';
    if(ca.strengths && ca.strengths.length){
      html += '<p><strong>Strengths:</strong></p><ul>';
      ca.strengths.forEach(function(s){ html += '<li>'+escapeHtml(s)+'</li>'; });
      html += '</ul>';
    }
    if(ca.weaknesses && ca.weaknesses.length){
      html += '<p><strong>Weaknesses:</strong></p><ul>';
      ca.weaknesses.forEach(function(w){ html += '<li>'+escapeHtml(w)+'</li>'; });
      html += '</ul>';
    }
    html += '</div></details></div>';
  }

  // Outcomes table
  if(sec.results && sec.results.outcomes_table && sec.results.outcomes_table.length){
    html += '<div class="trial-section"><details open><summary>Outcomes</summary><div class="section-body"><div style="overflow-x:auto"><table class="outcomes-table"><thead><tr><th>Outcome</th><th>Intervention</th><th>Control</th><th>Measure</th><th>Value</th><th>95% CI</th><th>P</th><th>Note</th></tr></thead><tbody>';
    sec.results.outcomes_table.forEach(function(r){
      html += '<tr><td>'+escapeHtml(r.outcome||'')+'</td><td>'+escapeHtml(r.group_a||'')+'</td><td>'+escapeHtml(r.group_b||'')+'</td><td>'+escapeHtml(r.effect_measure||'')+'</td><td>'+escapeHtml(r.effect_value||'')+'</td><td>'+escapeHtml(r.ci_95||'')+'</td><td>'+escapeHtml(r.p_value||'')+'</td><td>'+escapeHtml(r.note||'')+'</td></tr>';
    });
    html += '</tbody></table></div></div></details></div>';
  }

  // Subgroup table
  if(sec.results && sec.results.subgroup_table && sec.results.subgroup_table.length){
    html += '<div class="trial-section"><details><summary>Subgroup Analyses</summary><div class="section-body"><div style="overflow-x:auto"><table class="outcomes-table"><thead><tr><th>Subgroup</th><th>Intervention</th><th>Control</th><th>Measure</th><th>Value</th><th>95% CI</th><th>P-interaction</th></tr></thead><tbody>';
    sec.results.subgroup_table.forEach(function(r){
      html += '<tr><td>'+escapeHtml(r.subgroup||'')+'</td><td>'+escapeHtml(r.group_a||'')+'</td><td>'+escapeHtml(r.group_b||'')+'</td><td>'+escapeHtml(r.effect_measure||'')+'</td><td>'+escapeHtml(r.effect_value||'')+'</td><td>'+escapeHtml(r.ci_95||'')+'</td><td>'+escapeHtml(r.p_interaction||'')+'</td></tr>';
    });
    html += '</tbody></table></div></div></details></div>';
  }

  // Collapsible: background, methods, internal/external validity, strengths, limitations, etc.
  var collapsibleSections = [
    {key:'background', label:'Background &amp; Hypothesis'},
    {key:'methods', label:'Methods'},
    {key:'internal_validity', label:'Internal Validity'},
    {key:'external_validity', label:'External Validity'},
    {key:'safety', label:'Safety'},
    {key:'strengths', label:'Strengths'},
    {key:'limitations', label:'Limitations'},
    {key:'authors_conclusion', label:"Authors' Conclusion"},
    {key:'controversies', label:'Controversies'},
    {key:'context_related_trials', label:'Related Trials'},
    {key:'unresolved_questions', label:'Unresolved Questions'},
  ];

  collapsibleSections.forEach(function(cs){
    var val = sec[cs.key];
    if(!val) return;
    var content = '';
    if(Array.isArray(val)){
      content = '<ul>'+val.map(function(v){
        if(typeof v === 'string') return '<li>'+escapeHtml(v)+'</li>';
        if(v.topic && v.notes) return '<li><strong>'+escapeHtml(v.topic)+':</strong> '+escapeHtml(v.notes)+'</li>';
        if(v.domain && v.notes) return '<li><strong>'+escapeHtml(v.domain)+':</strong> '+escapeHtml(v.notes)+'</li>';
        if(v.trial && v.relation) return '<li><strong>'+escapeHtml(v.trial)+':</strong> '+escapeHtml(v.relation)+'</li>';
        return '<li>'+escapeHtml(JSON.stringify(v))+'</li>';
      }).join('')+'</ul>';
    } else if(typeof val === 'object'){
      var pairs = [];
      Object.keys(val).forEach(function(k){
        var v = val[k];
        var label = capitalizeFirst(k.replace(/_/g,' '));
        if(Array.isArray(v)){
          pairs.push('<p><strong>'+label+':</strong></p><ul>'+v.map(function(i){ return renderListItem(i); }).join('')+'</ul>');
        } else if(typeof v === 'object'){
          pairs.push('<p><strong>'+label+':</strong></p><ul>'+Object.keys(v).map(function(sk){ return '<li><strong>'+capitalizeFirst(sk.replace(/_/g,' '))+':</strong> '+escapeHtml(v[sk])+'</li>'; }).join('')+'</ul>');
        } else {
          pairs.push('<p><strong>'+label+':</strong> '+escapeHtml(v)+'</p>');
        }
      });
      content = pairs.join('');
    } else {
      content = '<p>'+escapeHtml(val)+'</p>';
    }
    if(content) html += '<div class="trial-section"><details><summary>'+cs.label+'</summary><div class="section-body">'+content+'</div></details></div>';
  });

  body.innerHTML = html;
  katexify(body);
}

// =====================================================================
// THEORY FLASHCARDS
// =====================================================================
function _theorySpecVar(spec){ return THEORY_SPEC_VAR[normalizeSpec(spec)] || '--spec-other'; }
function _theoryPill(spec, label){
  var v = _theorySpecVar(spec);
  return '<span class="pill" style="background:color-mix(in srgb, var('+v+') 18%, transparent); color:var('+v+')"><span class="dot" style="background:var('+v+')"></span>'+escapeHtml(label)+'</span>';
}
function _bmEnabled(){ return USER_IS_ADMIN || USER_FEATURES['bookmarks']; }
function _savedCardRefs(deckId){
    // Bookmark refs are flashcard:<uuid>; match via the locator.deck stored on save
  return Object.keys(_bookmarks.items || {}).filter(function(r){
    var it = _bookmarks.items[r];
    return it && it.locator && it.locator.deck === deckId;
  });
}
function theoryCardRef(deckId, cardId){ return 'flashcard:'+cardId; }
function theoryDeckFromCardId(cardId){
  for(var i=0;i<allFlashcardDecks.length;i++){
    for(var j=0;j<allFlashcardDecks[i].cards.length;j++){
      if(allFlashcardDecks[i].cards[j].id === cardId) return {deck: allFlashcardDecks[i], idx: j};
    }
  }
  return null;
}

// ---- Theory navigation helpers ----
function _theoryViewActive(){ return !!(document.getElementById('view-theory') && document.getElementById('view-theory').classList.contains('active')); }
function _theoryStudyVisible(){ var el = document.getElementById('theoryStudy'); return !!(el && el.style.display!=='none'); }

function theoryReset(){
  _currentDeck = null;
  _currentTheoryNote = null;
  _theoryListCollapsed = false;
  _theoryStudyFromList = false;
  _notesActiveSpecs = new Set();
  _notesActiveSubtopic = null;
  var st = document.getElementById('theoryStudy'); if(st) st.style.display='none';
  var cl = document.getElementById('theoryCardList'); if(cl) cl.style.display='none';
  var br = document.getElementById('theoryBrowser'); if(br) br.style.display='';
  var rd = document.getElementById('theoryNoteReader'); if(rd){ rd.style.display='none'; rd.innerHTML=''; }
  var nl = document.getElementById('theoryNotesList'); if(nl) nl.style.display='';
  var nc = document.getElementById('theoryNotesCount'); if(nc) nc.style.display='';
  var sr = document.getElementById('theoryNotesSearchRow'); if(sr) sr.style.display='';
  var sc = document.getElementById('theoryNotesChips'); if(sc) sc.style.display='';
}

function _focusCrumb(){
  var bar = document.getElementById('theoryCrumbs');
  if(!bar) return;
  var t = bar.querySelector('button.crumb-current') || bar.querySelector('button[data-crumb]');
  if(t && t.focus){ try{ t.focus({preventScroll:true}); } catch(e){ t.focus(); } }
}

function renderTheoryCrumbs(){
  var bar = document.getElementById('theoryCrumbs');
  if(!bar) return;
  if(!_theoryMode){ bar.style.display='none'; bar.innerHTML=''; return; }
  var parts = ['<button class="crumb" data-crumb="0" title="Back to all theory">All theory</button>'];
  if(_theoryMode==='notes'){
    parts.push('<span class="crumb-sep">&#8250;</span><button class="crumb'+( _currentTheoryNote?'':' crumb-current')+'" data-crumb="1" title="Back to notes list">Theory Topics</button>');
    if(_currentTheoryNote){
      parts.push('<span class="crumb-sep">&#8250;</span><span class="crumb crumb-current crumb-title" title="'+escapeHtml(_currentTheoryNote.title)+'">'+escapeHtml(_currentTheoryNote.title)+'</span>');
    }
  } else {
    parts.push('<span class="crumb-sep">&#8250;</span><button class="crumb'+( _currentDeck?'':' crumb-current')+'" data-crumb="1" title="Back to all decks">Flashcards</button>');
    if(_currentDeck){
      var studying = _theoryStudyVisible();
      parts.push('<span class="crumb-sep">&#8250;</span><button class="crumb'+( studying?'':' crumb-current')+'" data-crumb="2" title="Card list">'+escapeHtml(_currentDeck.title)+'</button>');
      if(studying){
        var posIdx = _theoryCardOrder.indexOf(_currentCardIdx); if(posIdx===-1) posIdx = 0;
        parts.push('<span class="crumb-sep">&#8250;</span><span class="crumb crumb-current">Card '+(posIdx+1)+' of '+_theoryCardOrder.length+'</span>');
      }
    }
  }
  bar.innerHTML = parts.join('');
  bar.style.display = 'flex';
}

function theoryGoTo(level){
  if(_theoryMode==='notes'){
    if(_currentTheoryNote && level<=1){ theoryNotesBack(); return; }
    if(level<=0){ theoryBackToHero(); }
    return;
  }
  if(level<=0){ theoryBackToHero(); return; }
  if(level===1){ theoryBackToBrowser(); return; }
  if(level===2 && _currentDeck && _theoryStudyVisible()){ theoryStudyToList(); }
}

function theoryStepBackFromStudy(){
  if(_theoryStudyFromList && _currentDeck) theoryStudyToList();
  else theoryBackToBrowser();
}

function _theoryHistoryURL(){
  if(_theoryMode==='notes'){
    var q = [];
    q.push('theory=notes');
    _notesActiveSpecs.forEach(function(s){ q.push('nspec='+encodeURIComponent(s)); });
    if(_notesActiveSubtopic) q.push('nsub='+encodeURIComponent(_notesActiveSubtopic));
    if(_notesSavedOnly) q.push('saved=1');
    if(_currentTheoryNote) q.push('note='+encodeURIComponent(_currentTheoryNote.id));
    else {
      var nq = (document.getElementById('theoryNotesSearch').value||'').trim();
      if(nq) q.push('q='+encodeURIComponent(nq));
    }
    return window.location.pathname+'?'+q.join('&');
  }
  if(_theoryMode==='flashcards'){
    var q = ['theory=flashcards'];
    if(_theorySavedOnly) q.push('saved=1');
    if(_currentDeck){
      q.push('system='+encodeURIComponent(_currentDeck.specialty));
      if(_theoryActiveSubtopic) q.push('subtopic='+encodeURIComponent(_theoryActiveSubtopic));
      if(_theoryStudyVisible()){
        var cur = _currentDeck.cards[_currentCardIdx];
        if(cur && cur.id) q.push('card='+encodeURIComponent(cur.id));
      } else {
        q.push('list=1');
        q.push('deck='+encodeURIComponent(_currentDeck.id));
      }
    } else {
      if(_theoryActiveSpecs.size===1) q.push('system='+encodeURIComponent(Array.from(_theoryActiveSpecs)[0]));
      if(_theoryActiveSubtopic) q.push('subtopic='+encodeURIComponent(_theoryActiveSubtopic));
      var dq = (document.getElementById('theorySearch').value||'').trim();
      if(dq) q.push('q='+encodeURIComponent(dq));
    }
    return window.location.pathname+'?'+q.join('&');
  }
  return null;
}

function _theoryPush(){
  if(_restoring) return;
  var u = _theoryHistoryURL();
  history.pushState({t:1}, '', u || window.location.pathname);
}

function _theoryReplace(){
  if(_restoring) return;
  var u = _theoryHistoryURL();
  history.replaceState({t:1}, '', u || window.location.pathname);
}

function _applyTheoryDeepLink(params){
  theoryReset();
  var theoryMode = params.get('theory');
  if(!theoryMode){ renderTheoryPane(null); return; }
  // Deep links open the Theory view itself (cold load lands on home otherwise)
  if(!_theoryViewActive()) showView('theory');
  if(theoryMode==='notes'){
    var nq = params.get('q');
    if(nq!=null) document.getElementById('theoryNotesSearch').value = nq;
    _notesSavedOnly = params.get('saved')==='1';
    _notesActiveSpecs = new Set((params.getAll('nspec')||[]).filter(Boolean));
    _notesActiveSubtopic = params.get('nsub');
    var nid = params.get('note');
    renderTheoryPane('notes');
    if(nid) openTheoryNote(nid);
    return;
  }
  if(theoryMode==='flashcards'){
    var sys = params.get('system');
    var sub = params.get('subtopic');
    var cid = params.get('card');
    var dck = params.get('deck');
    var dq = params.get('q');
    if(dq!=null) document.getElementById('theorySearch').value = dq;
    _theorySavedOnly = params.get('saved')==='1';
    _theoryActiveSubtopic = sub || null;
    _theoryActiveSpecs = sys
      ? new Set([normalizeSpec(sys)])
      : new Set(allFlashcardDecks.map(function(d){ return normalizeSpec(d.specialty); }));
    renderTheoryPane('flashcards');
    if(dck){
      var dhit = allFlashcardDecks.find(function(d){ return d.id===dck; });
      if(dhit){
        if(params.get('list')==='1') openTheoryCardList(dhit.id);
        else openTheoryDeck(dhit.id, 0);
      }
      return;
    }
    if(params.get('list')==='1' && sys && sub){
      var lhit = allFlashcardDecks.find(function(d){
        return d.id.toLowerCase() === (sys+'/'+sub).toLowerCase();
      });
      if(lhit) openTheoryCardList(lhit.id);
      return;
    }
    if(cid){
      var tRef = theoryDeckFromCardId(cid);
      if(tRef){
        _theoryActiveSpecs.add(tRef.deck.specialty);
        openTheoryDeck(tRef.deck.id, tRef.idx);
      }
      return;
    }
    if(sub && sys){
      var hit = allFlashcardDecks.find(function(d){
        return d.id.toLowerCase() === (sys+'/'+sub).toLowerCase();
      });
      if(hit) openTheoryDeck(hit.id, 0);
    }
  }
}

function katexify(root, allowSingle){
  // Render LaTeX delimiters ($$...$$, \\(...\\), \\[...\\]) inside a container.
  // Single-$ is disabled by default (currency amounts appear in pearls/notes);
  // theory notes pass allowSingle=true since clinical math ($z_q$, $\hat\theta$)
  // is written with single-$ there. Single-$ is listed LAST so $$...$$ wins.
  if(!root || typeof renderMathInElement !== 'function') return;
  try {
    var delims = [
      {left:'$$', right:'$$', display:true},
      {left:'\\(', right:'\\)', display:false},
      {left:'\\[', right:'\\]', display:true}
    ];
    if(allowSingle) delims.push({left:'$', right:'$', display:false});
    renderMathInElement(root, {
      delimiters:delims,
      throwOnError:false,
      strict:'ignore'
    });
  } catch(e){}
}

// ---- Theory Topics (markdown notes) ----
function _theoryFilteredNotes(){
  var q = (document.getElementById('theoryNotesSearch').value||'').toLowerCase().trim();
  return THEORY_NOTES.filter(function(n){
    if(_notesSavedOnly && !(_bookmarks.items && _bookmarks.items['note:'+n.id])) return false;
    if(_notesActiveSpecs.size && !_notesActiveSpecs.has(normalizeSpec(n.system))) return false;
    if(_notesActiveSubtopic && n.subtopic!==_notesActiveSubtopic) return false;
if(!q) return true;
    return (n.title+' '+n.md).toLowerCase().indexOf(q)!==-1;
  });
}

function theoryNoteNav(delta){
  if(!_currentTheoryNote) return;
  var order = _theoryFilteredNotes();
  var idx = -1;
  for(var i=0;i<order.length;i++){
    if(order[i].id===_currentTheoryNote.id){ idx=i; break; }
  }
  var ni = idx+delta;
  if(ni<0 || ni>=order.length) return;
  openTheoryNote(order[ni].id, true);
}

function renderTheoryNotes(){
  var q = (document.getElementById('theoryNotesSearch').value||'').toLowerCase().trim();
  var list = document.getElementById('theoryNotesList');
  var countEl = document.getElementById('theoryNotesCount');
  var box = document.getElementById('theoryNotesChips');
if(box){
    var savedCount = Object.keys(_bookmarks.items || {}).filter(function(r){ return r.indexOf('note:')===0; }).length;
    var specSet = {}, subSet = {};
    THEORY_NOTES.forEach(function(n){ var sys=normalizeSpec(n.system); specSet[sys]=(specSet[sys]||0)+1; subSet[sys+''+n.subtopic]=(subSet[sys+''+n.subtopic]||0)+1; });
    // Row 1: specialty chips — each pill is tinted in its encoded specialty colour
    var specChips = Object.keys(specSet).sort().map(function(s){
      var v = _theorySpecVar(s);
      return '<button class="chip'+( _notesActiveSpecs.has(s)?' active':'')+'" data-notes-spec="'+escapeHtml(s)+'" style="--chip-color:var('+v+')"><span class="dot" style="background:var('+v+')"></span>'+escapeHtml(s)+' <span class="chip-count">'+specSet[s]+'</span></button>';
    }).join('');
    var anyActive = _notesActiveSpecs.size>0 || _notesActiveSubtopic || _notesSavedOnly;
    var specRow = '<div class="notes-chip-row">'+specChips+
      '<button class="chip'+( _notesSavedOnly?' active':'')+'" data-notes-saved-only style="--chip-color:var(--accent)">&#128278; Saved ('+savedCount+')</button>'+
      (anyActive ? '<button class="chip" data-notes-clear-all style="--chip-color:var(--ink-muted)">&#10005; Clear</button>' : '')+'</div>';
    // Row 2: subtopic chips for the single active specialty — below a separator
    var subRow = '';
    if(_notesActiveSpecs.size===1){
      var onlySpec = Array.from(_notesActiveSpecs)[0];
      var subChips = Object.keys(subSet).filter(function(k){ return k.indexOf(onlySpec+'')===0; }).sort().map(function(k){
        var sub = k.split('')[1];
        var v = _theorySpecVar(onlySpec);
        return '<button class="chip'+( _notesActiveSubtopic===sub?' active':'')+'" data-notes-sub="'+escapeHtml(sub)+'" style="--chip-color:var('+v+')">'+escapeHtml(sub)+' <span class="chip-count">'+subSet[k]+'</span></button>';
      }).join('');
      if(subChips){ subRow = '<div class="notes-chip-sep"></div><div class="notes-chip-row">'+subChips+'</div>'; }
    }
    box.innerHTML = '<div class="notes-chip-wrap">'+specRow+subRow+'</div>';
  }
  if(!THEORY_NOTES.length){
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#128214;</span><p>No theory notes yet. Drop markdown files into <span class="mono">output_files/Theory MDs/</span>.</p></div>';
    if(countEl) countEl.textContent = '';
    return;
  }
  var filtered = _theoryFilteredNotes();
  list.innerHTML = filtered.map(function(n){
    var saved = !!(_bookmarks.items && _bookmarks.items['note:'+n.id]);
    return '<button class="doc-card" data-theory-note="'+escapeHtml(n.id)+'">'+
      '<div class="doc-stripe" style="background:var(--accent)"></div>'+
      '<div class="doc-inner">'+
        '<div class="doc-top"><span class="type-tag">'+escapeHtml(n.system||'Note')+'</span>'+(n.subtopic && n.subtopic!=='General' ? '<span class="theory-sub-tag">'+escapeHtml(n.subtopic)+'</span>':'')+(saved?'<span class="theory-saved-badge">&#128278; saved</span>':'')+'</div>'+
        '<p class="doc-title">'+escapeHtml(n.title)+'</p>'+
        '<p class="doc-snippet">'+escapeHtml(n.md.replace(/\s+/g,' ').substring(0,110))+'</p>'+
      '</div>'+
    '</button>';
  }).join('');
  if(countEl) countEl.textContent = filtered.length ? 'Showing '+filtered.length+' of '+THEORY_NOTES.length+' notes' : '';
}

function _theoryMarkdownHTML(md){
  // Degrade footnote syntax: drop [^n] references and [^n]: definition lines
  var out = String(md||'');
  out = out.replace(/^\[\^[^\]]+\]:\s*.*$/gm, '');
  out = out.replace(/\[\^[^\]]+\]/g, '');
  try {
    var html = marked.parse(out);
    html = html.replace(/<table>[\s\S]*?<\/table>/g, function(t){
      return '<button class="theory-table-expand" data-theory-table-open type="button"><span class="tt-expand-icon">&#8693;</span> Full view</button>'+
             '<div class="theory-table-wrap" data-theory-table-open>'+t+'</div>';
    });
    return html;
  } catch(e){ return '<pre>'+escapeHtml(out)+'</pre>'; }
}

function openTheoryNote(noteId, fromReader){
  var note = THEORY_NOTES.find(function(n){ return n.id===noteId; });
  if(!note) return;
  _currentTheoryNote = note;
  renderTheoryPane('notes');
  document.getElementById('theoryNotesSearchRow').style.display = 'none';
  document.getElementById('theoryNotesChips').style.display = 'none';
  document.getElementById('theoryNotesList').style.display = 'none';
  document.getElementById('theoryNotesCount').style.display = 'none';
  var ref = 'note:'+note.id;
  registerBookmarkMeta(ref, {kind:'note', title: note.title, system: 'Theory Topics', type: 'Note', locator: {noteId: note.id}});
  var saveBtn = _bmEnabled() ? bookmarkBtnHTML(ref) : '';
  var reader = document.getElementById('theoryNoteReader');
  reader.style.display = 'block';
  var order = _theoryFilteredNotes();
  var idx = -1;
  for(var i=0;i<order.length;i++){ if(order[i].id===note.id){ idx=i; break; } }
  var prevBtn = idx>0 ? '<button class="btn nav-btn" data-theory-note-nav="-1" title="Previous note">&#9664; Prev</button>' : '';
  var nextBtn = (idx>=0 && idx<order.length-1) ? '<button class="btn nav-btn" data-theory-note-nav="1" title="Next note">Next &#9654;</button>' : '';
  reader.innerHTML =
    '<div class="theory-card-head theory-note-head">'+
      '<div class="notes-title-row">'+
        _theoryPill(note.system||'General', note.title)+
        (note.subtopic && note.subtopic!=='General' ? '<span class="theory-sub-tag">'+escapeHtml(note.subtopic)+'</span>' : '')+
      '</div>'+
      '<div class="notes-nav-row">'+prevBtn+nextBtn+'</div>'+
      '<div class="notes-tools-row">'+
        exportNoteBtnHTML(note)+
        '<button class="related-btn" data-open-related="theory:'+escapeHtml(note.rel||'')+'" title="Related papers, guidelines, decks &amp; pearls">&#128279; Related</button>'+
        saveBtn+
      '</div>'+
      '<div class="notes-font-row"><span class="notes-font-label">Text&nbsp;size</span>'+theoryFontChipsHTML('notes')+'</div>'+
    '</div>'+
    '<article class="theory-note" id="theoryNoteArticle">'+_theoryMarkdownHTML(note.md)+'</article>';
  applyTheoryFont('notes');
  katexify(document.getElementById('theoryNoteArticle'), true);
  renderTheoryCrumbs();
  if(fromReader) _theoryReplace(); else _theoryPush();
  _focusCrumb();
  window.scrollTo({top:0, behavior:'instant'});
}

function theoryNotesBack(){
  document.getElementById('theoryNoteReader').style.display = 'none';
  document.getElementById('theoryNoteReader').innerHTML = '';
  document.getElementById('theoryNotesList').style.display = '';
  document.getElementById('theoryNotesCount').style.display = '';
  document.getElementById('theoryNotesSearchRow').style.display = '';
  document.getElementById('theoryNotesChips').style.display = '';
  _currentTheoryNote = null;
  renderTheoryNotes();
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
  window.scrollTo({top:0, behavior:'instant'});
}

/* ---- Theory table full-view overlay ---- */
function openTheoryTableOverlay(src){
  var table = null;
  if(src){
    var wrap = (typeof src.closest==='function' && src.closest('.theory-table-wrap')) ||
      (src.nextElementSibling && src.nextElementSibling.classList && src.nextElementSibling.classList.contains('theory-table-wrap') ? src.nextElementSibling : null);
    if(wrap) table = wrap.querySelector('table');
  }
  if(!table && src && src.tagName==='TABLE') table = src;
  if(!table) return;
  var title = (_currentTheoryNote && _currentTheoryNote.title) ? _currentTheoryNote.title : 'Table';
  var inner = document.getElementById('theoryTableFitInner');
  inner.innerHTML = '';
  inner.appendChild(table.cloneNode(true));
  document.getElementById('theoryTableOverlayTitle').textContent = title + ' · Table';
  var scrollEl = document.getElementById('theoryTableOverlayScroll');
  scrollEl.scrollTop = 0; scrollEl.scrollLeft = 0;
  _theoryTableFitActive = false;
  scrollEl.classList.remove('fit');
  inner.style.zoom = '';
  var fitBtn = document.querySelector('[data-theory-table-fit]');
  if(fitBtn) fitBtn.textContent = 'Fit width';
  document.getElementById('theoryTableOverlay').style.display = 'flex';
  document.body.style.overflow = 'hidden';
  _theoryTableOverlayOpen = true;
  var ov = document.getElementById('theoryTableOverlay');
  var fsReq = ov.requestFullscreen || ov.webkitRequestFullscreen;
  if(fsReq){
    var p = fsReq.call(ov);
    if(p && p.catch) p.catch(function(){});
  }
}

function closeTheoryTableOverlay(){
  if(!_theoryTableOverlayOpen) return;
  if(document.fullscreenElement || document.webkitFullscreenElement){
    var p = (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    if(p && p.catch) p.catch(finishCloseTheoryTableOverlay);
    return;
  }
  finishCloseTheoryTableOverlay();
}

function finishCloseTheoryTableOverlay(){
  document.getElementById('theoryTableOverlay').style.display = 'none';
  document.getElementById('theoryTableFitInner').innerHTML = '';
  document.body.style.overflow = '';
  _theoryTableOverlayOpen = false;
  _theoryTableFitActive = false;
}

function theoryTableToggleFit(){
  if(!_theoryTableOverlayOpen) return;
  _theoryTableFitActive = !_theoryTableFitActive;
  var scrollEl = document.getElementById('theoryTableOverlayScroll');
  var inner = document.getElementById('theoryTableFitInner');
  var btn = document.querySelector('[data-theory-table-fit]');
  if(_theoryTableFitActive){
    scrollEl.classList.add('fit');
    if(btn) btn.textContent = 'Fit: off';
    theoryTableApplyFit();
  } else {
    scrollEl.classList.remove('fit');
    inner.style.zoom = '';
    if(btn) btn.textContent = 'Fit width';
  }
}

function theoryTableApplyFit(){
  if(!_theoryTableFitActive) return;
  var scrollEl = document.getElementById('theoryTableOverlayScroll');
  var inner = document.getElementById('theoryTableFitInner');
  var table = inner.querySelector('table');
  if(!table) return;
  var avail = scrollEl.clientWidth - 28;
  var scale = Math.min(1, avail / (table.scrollWidth || 1));
  inner.style.zoom = scale >= 1 ? '' : String(scale);
}

document.addEventListener('fullscreenchange', function(){
  if(_theoryTableOverlayOpen && !document.fullscreenElement) finishCloseTheoryTableOverlay();
});
document.addEventListener('webkitfullscreenchange', function(){
  if(_theoryTableOverlayOpen && !document.webkitFullscreenElement) finishCloseTheoryTableOverlay();
});
window.addEventListener('resize', function(){
  if(_theoryTableOverlayOpen && _theoryTableFitActive) theoryTableApplyFit();
});

function renderTheoryPane(mode){
  if(mode==='hero') mode = null;
  _theoryMode = mode || null;
  var hero = document.getElementById('theoryHero');
  var notes = document.getElementById('theoryNotesPane');
  var cards = document.getElementById('theoryFlashcardsPane');
  if(!hero || !notes || !cards) return;
  hero.style.display = _theoryMode ? 'none' : '';
  notes.style.display = _theoryMode==='notes' ? '' : 'none';
  cards.style.display = _theoryMode==='flashcards' ? '' : 'none';
  if(_theoryMode==='notes'){ renderTheoryNotes(); }
  if(_theoryMode==='flashcards'){ renderTheoryChips(); renderTheoryDecks(); }
  renderTheoryCrumbs();
}

function theoryBackToHero(){
  theoryReset();
  renderTheoryPane(null);
  renderTheoryCrumbs();
  _theoryPush();
  window.scrollTo({top:0, behavior:'instant'});
}

function renderTheoryChips(){
  var box = document.getElementById('theoryChips');
  if(!box) return;
  if(_theoryActiveSpecs.size!==1) _theoryActiveSubtopic = null;
  var counts = {};
  allFlashcardDecks.forEach(function(d){ var sys=normalizeSpec(d.specialty); counts[sys] = (counts[sys]||0)+1; });
  var html = Object.keys(counts).sort().map(function(s){
    var active = _theoryActiveSpecs.has(s);
    return '<button class="chip '+(active?'active':'')+'" data-theory-chip="'+escapeHtml(s)+'" style="--chip-color:var('+_theorySpecVar(s)+')"><span class="dot" style="background:var('+_theorySpecVar(s)+')"></span>'+escapeHtml(s)+' ('+counts[s]+')</button>';
  }).join('');
  var savedCount = Object.keys(_bookmarks.items || {}).filter(function(r){ return r.indexOf('flashcard:')===0; }).length;
  html += '<button class="chip'+( _theorySavedOnly?' active':'')+'" data-theory-saved-only style="--chip-color:var(--accent)">&#128278; Saved ('+savedCount+')</button>';
  box.innerHTML = html + '<button class="chip" data-theory-chip-reset>Reset</button><button class="chip" data-theory-chip-uncheck>Uncheck all</button>';
  renderTheorySubtopicChips();
}

function renderTheorySubtopicChips(){
  var box = document.getElementById('theorySubtopicChips');
  if(!box) return;
  if(_theoryActiveSpecs.size!==1){
    box.innerHTML = '';
    return;
  }
  var spec = Array.from(_theoryActiveSpecs)[0];
  var subs = THEORY_SUBTOPIC_MAP[spec] || [];
  if(!subs.length){
    box.innerHTML = '';
    return;
  }
  var deckCounts = {};
  allFlashcardDecks.forEach(function(d){
    if(normalizeSpec(d.specialty)!==spec) return;
    (d.subtopics||[]).forEach(function(t){ deckCounts[t] = (deckCounts[t]||0)+1; });
  });
  var html = '<span class="pearl-count" style="margin:0 6px 0 0;flex:0 0 auto">Subtopic:</span>';
  html += subs.map(function(t){
    var active = _theoryActiveSubtopic===t;
    return '<button class="chip'+(active?' active':'')+'" data-theory-subtopic="'+escapeHtml(t)+'" style="--chip-color:var('+_theorySpecVar(spec)+')">'+escapeHtml(t)+(deckCounts[t]?' ('+deckCounts[t]+')':'')+'</button>';
  }).join('');
  if(_theoryActiveSubtopic) html += '<button class="chip" data-theory-subtopic-clear style="--chip-color:var(--ink-muted)">&#10005; Clear</button>';
  box.innerHTML = html;
}

function renderTheoryDecks(){
  var q = (document.getElementById('theorySearch').value||'').toLowerCase().trim();
  var list = document.getElementById('theoryDeckList');
  var countEl = document.getElementById('theoryCount');
  if(!allFlashcardDecks.length){
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#129504;</span><p>No flashcard decks yet. Drop files under <span class="mono">flashcards_input/{Specialty}/</span> (md = authored deck, pdf/txt/docx/html = raw material) and run <span class="mono">python flashcards.py</span>.</p></div>';
    if(countEl) countEl.textContent = '';
    return;
  }
  var filtered = allFlashcardDecks.filter(function(d){
    if(!_theoryActiveSpecs.has(normalizeSpec(d.specialty))) return false;
    var savedRefs = _savedCardRefs(d.id);
    if(_theorySavedOnly && !savedRefs.length) return false;
    if(_theoryActiveSubtopic && (d.subtopics||[]).indexOf(_theoryActiveSubtopic)===-1) return false;
    if(q){
      var hay = (d.title+' '+d.specialty+' '+d.subtopics.join(' ')+' '+d.cards.map(function(c){ return c.subtopic+' '+(c.front||'')+' '+(c.back||'')+' '+(c.tags||[]).join(' '); }).join(' ')).toLowerCase();
      if(hay.indexOf(q)===-1) return false;
    }
    return true;
  });
  var html = filtered.map(function(d){
    var savedRefs = _savedCardRefs(d.id);
    var savedBadge = savedRefs.length ? '<span class="theory-saved-badge">&#128278; '+savedRefs.length+'</span>' : '';
    var snip = (d.subtopics||[]).length ? (d.subtopics||[]).slice(0,4).join(' · ') : d.cards.map(function(c){ return c.subtopic; }).slice(0,3).join(' · ');
    return '<button class="doc-card" data-theory-deck="'+escapeHtml(d.id)+'">'+
      '<div class="doc-stripe" style="background:var('+_theorySpecVar(d.specialty)+')"></div>'+
      '<div class="doc-inner">'+
        '<div class="doc-top">'+_theoryPill(d.specialty, d.specialty)+'<span class="type-tag">'+d.cards.length+' card'+(d.cards.length===1?'':'s')+'</span>'+savedBadge+'</div>'+
        '<p class="doc-title">'+escapeHtml(d.title)+'</p>'+
        '<p class="doc-snippet">'+escapeHtml(snip)+'</p>'+
      '</div>'+
    '</button>';
  }).join('');
  list.innerHTML = html || '<p style="color:var(--ink-muted);padding:20px 4px">No decks match these filters.</p>';
  if(countEl) countEl.textContent = 'Showing '+filtered.length+' of '+allFlashcardDecks.length+' decks';
}

function openTheoryDeck(deckId, cardIdxOrId, smooth){
  var deck = allFlashcardDecks.find(function(d){ return d.id===deckId; });
  if(!deck) return;
  _currentDeck = deck;
  _theoryStudyFromList = false;
  _theoryListCollapsed = false;
  _theoryActiveSpecs.add(deck.specialty);
  renderTheoryPane('flashcards');
  _theoryCardOrder = _theoryActiveSubtopic
    ? deck.cards.map(function(c, i){ return (c.tags||[]).indexOf(_theoryActiveSubtopic)>-1 ? i : -1; }).filter(function(i){ return i>-1; })
    : deck.cards.map(function(c, i){ return i; });
  if(!_theoryCardOrder.length) _theoryCardOrder = deck.cards.map(function(c, i){ return i; });
  var start = 0;
  if(typeof cardIdxOrId==='number') start = (cardIdxOrId>=0 && cardIdxOrId<deck.cards.length) ? cardIdxOrId : _theoryCardOrder[0];
  else if(typeof cardIdxOrId==='string'){
    var byId = deck.cards.findIndex(function(c){ return c.id===cardIdxOrId; });
    start = byId>-1 ? byId : _theoryCardOrder[0];
  } else {
    start = _theoryCardOrder[0];
  }
  if(_theoryActiveSubtopic && _theoryCardOrder.indexOf(start)===-1) start = _theoryCardOrder[0];
  _currentCardIdx = start;
  _theoryFlipped = false;
  document.getElementById('theoryBrowser').style.display = 'none';
  document.getElementById('theoryStudy').style.display = 'block';
  renderTheoryCard();
  if(smooth) theoryScrollToStudy();
  _theoryPush();
  _focusCrumb();
}

function theoryBackToBrowser(){
  _currentDeck = null;
  _theoryListCollapsed = false;
  _theoryStudyFromList = false;
  document.getElementById('theoryStudy').style.display = 'none';
  document.getElementById('theoryCardList').style.display = 'none';
  document.getElementById('theoryBrowser').style.display = '';
  renderTheoryDecks();
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
  window.scrollTo({top:0, behavior:'instant'});
}

function theoryStudyToList(){
  if(!_currentDeck) return;
  _theoryListCollapsed = false;
  renderTheoryCardList();
  document.getElementById('theoryStudy').style.display = 'none';
  document.getElementById('theoryCardList').style.display = 'block';
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
  window.scrollTo({top:0, behavior:'instant'});
}

function openTheoryCardList(deckId){
  var deck = allFlashcardDecks.find(function(d){ return d.id===deckId; });
  if(!deck) return;
  renderTheoryPane('flashcards');
  _currentDeck = deck;
  _theoryStudyFromList = false;
  _theoryListCollapsed = false;
  _theoryActiveSpecs.add(deck.specialty);
  document.getElementById('theoryBrowser').style.display = 'none';
  document.getElementById('theoryStudy').style.display = 'none';
  document.getElementById('theoryCardList').style.display = 'block';
  renderTheoryCardList();
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
}

function renderTheoryCardList(){
  var deck = _currentDeck;
  if(!deck) return;
  var filtered = _theoryActiveSubtopic
    ? deck.cards.filter(function(c){ return (c.tags||[]).indexOf(_theoryActiveSubtopic)>-1; })
    : deck.cards;
  if(!filtered.length) filtered = deck.cards;
  var collapsed = !!_theoryListCollapsed;
  var toggleLabel = collapsed
    ? filtered.length+' card'+(filtered.length===1?'':'s')+' &middot; show list'
    : 'Collapse list';
  var toggleCaret = collapsed ? '&#9660;' : '&#9650;';
  document.getElementById('theoryCardListHead').innerHTML =
    _theoryPill(deck.specialty, deck.title)+
    '<button class="related-btn" data-open-related="deck:'+escapeHtml(deck.id)+'" title="Related papers, guidelines, theory notes &amp; pearls">&#128279; Related</button>'+
    '<button class="theory-list-toggle" data-theory-list-toggle title="'+(collapsed?'Show the card list':'Hide the card list')+'"><span class="theory-toggle-caret">'+toggleCaret+'</span><span>'+toggleLabel+'</span></button>';
  var countEl = document.getElementById('theoryCardListCount');
  countEl.style.display = collapsed ? 'none' : '';
  countEl.textContent = filtered.length===deck.cards.length
    ? 'Showing '+filtered.length+' card'+(filtered.length===1?'':'s')
    : 'Showing '+filtered.length+' of '+deck.cards.length+' cards (filtered to '+escapeHtml(_theoryActiveSubtopic)+')';
  var body = document.getElementById('theoryCardListBody');
  body.style.display = collapsed ? 'none' : '';
  body.innerHTML = filtered.map(function(c){
    var saved = !!(_bookmarks.items && _bookmarks.items[theoryCardRef(deck.id, c.id)]);
    return '<button class="pearl-row" data-theory-card-open="'+c.id+'">'+
      '<span class="dot" style="background:var('+_theorySpecVar(deck.specialty)+')"></span>'+
      '<span class="txt">'+escapeHtml((c.front||c.subtopic||'Card').substring(0,160))+'<span class="src">'+(c.tags||[]).join(' · ')+(saved?' · saved':'')+'</span></span>'+
    '</button>';
  }).join('') || '<p style="color:var(--ink-muted);padding:20px 4px">No cards match this subtopic.</p>';
  renderTheoryCrumbs();
}

function theoryScrollToStudy(){
  var st = document.getElementById('theoryStudy');
  if(st) st.scrollIntoView({block:'start', behavior:'smooth'});
}

function theoryFontSize(scope){
  var k = 'hackccm_theoryFont_'+scope;
  try {
    var v = parseFloat(localStorage.getItem(k)||'');
    if(v && v>=0.7 && v<=2) return v;
  } catch(e){}
  return 1;
}

function theoryFontChipsHTML(scope){
  var cur = theoryFontSize(scope);
  var sizes = [
    {v:0.85, px:11},
    {v:0.925, px:12},
    {v:1, px:13},
    {v:1.1, px:14},
    {v:1.25, px:15},
  ];
  return sizes.map(function(s){
    return '<button class="size-chip'+(Math.abs(cur-s.v)<0.001?' active':'')+'" data-theory-font="'+scope+'" data-theory-font-val="'+s.v+'" style="font-size:'+s.px+'px" title="Text size">A</button>';
  }).join('');
}

function applyTheoryFont(scope){
  var v = theoryFontSize(scope);
  if(scope==='notes'){
    var art = document.getElementById('theoryNoteArticle');
    if(art) art.style.setProperty('--theory-note-fs', v+'rem');
  } else {
    var stage = document.getElementById('theoryCardStage');
    if(stage) stage.style.setProperty('--theory-card-fs', v+'rem');
  }
}

function theoryNav(delta){
  if(!_currentDeck) return;
  var pos = _theoryCardOrder.indexOf(_currentCardIdx);
  var nextPos = pos + delta;
  if(nextPos<0 || nextPos>=_theoryCardOrder.length) return;
  _currentCardIdx = _theoryCardOrder[nextPos];
  _theoryFlipped = false;
  renderTheoryCard();
  _theoryReplace();
}

function renderTheoryCard(){
  if(!_currentDeck) return;
  var deck = _currentDeck;
  var posIdx = _theoryCardOrder.indexOf(_currentCardIdx);
  if(posIdx===-1) posIdx = 0;
  var card = deck.cards[_currentCardIdx];
  var total = _theoryCardOrder.length;
  var filtered = !!_theoryActiveSubtopic;
  var ref = theoryCardRef(deck.id, card.id);

  registerBookmarkMeta(ref, {kind:'flashcard', title: card.subtopic || deck.title, system: deck.specialty, type: 'Flashcard', locator: {deck: deck.id, card: card.id, cardIdx: _currentCardIdx}});

  var saveBtn = _bmEnabled() ? bookmarkBtnHTML(ref) : '';
  var modeToggles = '<button class="theory-mode-chip'+( _theoryViewMode==='single'?' active':'')+'" data-theory-mode="single">Single face</button><button class="theory-mode-chip'+( _theoryViewMode==='flip'?' active':'')+'" data-theory-mode="flip">Flip card</button>';

  document.getElementById('theoryStudyHead').innerHTML =
    _theoryPill(deck.specialty, deck.title)+
    '<span class="theory-card-progress">Card '+(posIdx+1)+' of '+total+(filtered?' (filtered)':'')+'</span>'+
    '<button class="btn nav-btn" data-theory-list-open title="Show the card list">List &#9776;</button>'+
    saveBtn;

  var tagRow = (card.tags||[]).length ? card.tags.map(function(t){
    return '<span class="theory-tag-pill'+(filtered && t===_theoryActiveSubtopic?' hot':'')+'">'+escapeHtml(t)+'</span>';
  }).join('') : '';
  if(filtered) tagRow += '<button class="theory-tag-pill" data-theory-tag-clear title="Clear subtopic filter">'+escapeHtml(_theoryActiveSubtopic)+' <span class="theory-tag-x">&#10005;</span></button>';
  document.getElementById('theoryCardTags').innerHTML = tagRow;

  var stage = document.getElementById('theoryCardStage');
  var frontHTML = (card.front||'').trim() ? marked.parse(card.front) : '<h3>'+escapeHtml(card.subtopic)+'</h3>';
  var backHTML = marked.parse(card.back||'');
  if(_theoryViewMode==='flip'){
    stage.innerHTML =
      '<div class="theory-card-wrap'+( _css3d?'':' no-3d')+'"><div class="theory-card-inner flip'+( _theoryFlipped?' flipped':'')+'" id="theoryFlipInner">'+
        '<div class="theory-face front theory-card-content"><div class="theory-front-big">'+frontHTML+'</div><span class="flip-hint">tap to flip ⇅</span></div>'+
        '<div class="theory-face back theory-card-content">'+backHTML+'<span class="flip-hint">tap to flip ⇅</span></div>'+
      '</div></div>';
  } else {
    var frontText = (card.front||'').trim();
    var qHTML;
    if(!frontText){
      qHTML = '<h3 class="theory-card-question">'+escapeHtml(card.subtopic||deck.title)+'</h3>';
    } else {
      var qBody = marked.parse(frontText).trim().replace(/^<p>\s*/,'').replace(/\s*<\/p>$/,'');
      var qBlock = /<(p|div|ul|ol|table|blockquote|h[1-6])\s*>/i.test(qBody);
      qHTML = qBlock
        ? '<div class="theory-card-question">'+qBody+'</div>'
        : '<h3 class="theory-card-question">'+qBody+'</h3>';
    }
    stage.innerHTML = qHTML + '<div class="theory-card-flat theory-card-content">'+backHTML+'</div>';
  }
  katexify(stage);
  applyTheoryFont('cards');

  var prevBtn = '<button class="btn nav-btn"'+(posIdx===0?' disabled':'')+' data-theory-nav="-1">&#9664; Previous</button>';
  var nextBtn = posIdx<total-1
    ? '<button class="btn nav-btn" data-theory-nav="1">Next &#9654;</button>'
    : '<button class="btn nav-btn" data-theory-done>Done &#10004;</button>';
  document.getElementById('theoryCardNav').innerHTML = prevBtn + nextBtn + modeToggles + theoryFontChipsHTML('cards');

  document.getElementById('theoryCardDots').innerHTML = _theoryCardOrder.map(function(ci, pi){
    var c = deck.cards[ci];
    var saved = !!(_bookmarks.items && _bookmarks.items[theoryCardRef(deck.id, c.id)]);
    return '<button class="theory-dot'+( pi===posIdx?' active':'')+( saved?' saved':'')+'" data-theory-dot="'+pi+'" title="Card '+(pi+1)+' of '+total+'"></button>';
  }).join('');
  renderTheoryCrumbs();
}

function theorySetViewMode(mode){
  _theoryViewMode = mode;
  _theoryFlipped = false;
  renderTheoryCard();
}

// =====================================================================
// BOOKMARKS
// =====================================================================
function registerBookmarkMeta(ref, meta){ _bookmarkMeta[ref] = meta || {}; }

function bookmarkBtnHTML(ref, label){
  var active = !!(_bookmarks.items && _bookmarks.items[ref]);
  return '<button class="icon-btn bookmark-btn'+(active?' active':'')+'" data-bookmark-toggle="'+escapeHtml(ref)+'" aria-label="'+(active?'Remove bookmark':'Add bookmark')+'" title="'+(active?'Remove bookmark':'Add bookmark')+'">'+(label||'&#128278;')+'</button>';
}

function exportPaperBtnHTML(entry){
  var qs = 'kind=paper&file_name='+encodeURIComponent(entry.file_name||'')+'&system='+encodeURIComponent(entry.system||'General')+'&type='+encodeURIComponent(entry.type||'Other');
  return '<button class="btn nav-btn" data-export-paper="'+escapeHtml(qs)+'" title="Open a printable version of this summary in a new window">&#128196; PDF</button>';
}

function exportNoteBtnHTML(note){
  var qs = 'kind=note&file_name='+encodeURIComponent(note.id||'')+'&title='+encodeURIComponent((note.title||'').substring(0,120));
  return '<button class="btn nav-btn" data-export-note="'+escapeHtml(qs)+'" title="Open a printable version of this note in a new window">&#128196; PDF </button>';
}

function refreshBookmarkButtons(){
  document.querySelectorAll('[data-bookmark-toggle]').forEach(function(btn){
    var ref = btn.dataset.bookmarkToggle;
    var active = !!(_bookmarks.items && _bookmarks.items[ref]);
    btn.classList.toggle('active', active);
    btn.title = active ? 'Remove bookmark' : 'Add bookmark';
    btn.setAttribute('aria-label', active ? 'Remove bookmark' : 'Add bookmark');
  });
}

function updateBookmarkCounts(){
  var n = Object.keys(_bookmarks.items || {}).length;
  ['bookmarksTopCount','bookmarksDrawerCount'].forEach(function(id){
    var el = document.getElementById(id);
    if(el){ el.textContent = n; el.classList.toggle('zero', n===0); }
  });
  var c = document.getElementById('bookmarksCount');
  if(c) c.textContent = n + ' saved';
}

function loadBookmarks(){
  if(!USER_IS_ADMIN && !USER_FEATURES['bookmarks']) return;
  fetch('/api/bookmarks').then(function(r){ return r.json(); }).then(function(data){
    if(data && data.items) _bookmarks = data;
    else _bookmarks = {items: {}, folders: {}};
    updateBookmarkCounts(); refreshBookmarkButtons();
  }).catch(function(){});
}

function toggleBookmark(ref, btn){
  if(!_bookmarks.items) _bookmarks.items = {};
  if(_bookmarks.items[ref]){
    fetch('/api/bookmarks?ref='+encodeURIComponent(ref), {method:'DELETE'}).then(function(r){ return r.json(); }).then(function(d){
      delete _bookmarks.items[ref];
      updateBookmarkCounts(); refreshBookmarkButtons();
      if(document.querySelector('.view.active').id==='view-bookmarks') renderBookmarks();
      showToast('Bookmark removed');
    }).catch(function(){ showToast('Failed &mdash; try again'); });
  } else {
    var meta = _bookmarkMeta[ref] || {};
    var payload = {
      ref: ref,
      kind: meta.kind || 'paper',
      title: meta.title || 'Untitled',
      system: meta.system || 'General',
      type: meta.type || '',
      locator: meta.locator || {}
    };
    fetch('/api/bookmarks', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(function(r){ return r.json(); }).then(function(d){
      if(d && d.item) _bookmarks.items[ref] = d.item;
      updateBookmarkCounts(); refreshBookmarkButtons();
      if(document.querySelector('.view.active').id==='view-bookmarks') renderBookmarks();
      showToast('Bookmark saved');
    }).catch(function(){ showToast('Failed &mdash; try again'); });
  }
}

function removeBookmark(ref){
  if(!(_bookmarks.items && _bookmarks.items[ref])) return;
  fetch('/api/bookmarks?ref='+encodeURIComponent(ref), {method:'DELETE'}).then(function(r){ return r.json(); }).then(function(d){
    delete _bookmarks.items[ref];
    updateBookmarkCounts(); refreshBookmarkButtons(); renderBookmarks();
  }).catch(function(){ showToast('Failed &mdash; try again'); });
}

function setBookmarkFolder(ref, folder){
  fetch('/api/bookmarks', {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ref: ref, folder: folder || null})}).then(function(r){ return r.json(); }).then(function(d){
    if(d && d.item) _bookmarks.items[ref] = d.item;
    renderBookmarks();
  }).catch(function(){ showToast('Failed &mdash; try again'); });
}

function setBookmarkTags(ref, raw){
  var tags = String(raw||'').split(',').map(function(t){ return t.trim(); }).filter(function(t){ return t; }).slice(0,20);
  fetch('/api/bookmarks', {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ref: ref, tags: tags})}).then(function(r){ return r.json(); }).then(function(d){
    if(d && d.item) _bookmarks.items[ref] = d.item;
    renderBookmarks();
  }).catch(function(){ showToast('Failed &mdash; try again'); });
}

function createBookmarkFolder(){
  var nameEl = document.getElementById('bookmarksNewFolderName');
  var name = (nameEl.value||'').trim();
  if(!name) return;
  fetch('/api/bookmarks/folders', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name: name, color: _bmNewFolderColor})}).then(function(r){ return r.json(); }).then(function(d){
    if(d && d.id){
      if(!_bookmarks.folders) _bookmarks.folders = {};
      _bookmarks.folders[d.id] = d.folder;
    }
    nameEl.value = '';
    document.getElementById('bookmarksNewFolderRow').classList.remove('show');
    renderBookmarks();
  }).catch(function(){ showToast('Failed &mdash; try again'); });
}

function renameBookmarkFolder(fid){
  var f = _bookmarks.folders && _bookmarks.folders[fid];
  if(!f) return;
  var name = prompt('Folder name', f.name);
  if(!name || !name.trim()) return;
  fetch('/api/bookmarks/folders', {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id: fid, name: name.trim()})}).then(function(r){ return r.json(); }).then(function(d){
    if(d && d.folder && _bookmarks.folders) _bookmarks.folders[fid] = d.folder;
    renderBookmarks();
  }).catch(function(){ showToast('Failed &mdash; try again'); });
}

function deleteBookmarkFolder(fid){
  if(!confirm('Delete this folder? Bookmarks inside will move to Uncategorized.')) return;
  fetch('/api/bookmarks/folders?ref='+encodeURIComponent(fid), {method:'DELETE'}).then(function(r){ return r.json(); }).then(function(d){
    if(_bookmarks.folders && _bookmarks.folders[fid]) delete _bookmarks.folders[fid];
    Object.keys(_bookmarks.items||{}).forEach(function(ref){ if(_bookmarks.items[ref].folder===fid) _bookmarks.items[ref].folder = null; });
    if(_bookmarksFolderFilter===fid) _bookmarksFolderFilter = null;
    renderBookmarks();
  }).catch(function(){ showToast('Failed &mdash; try again'); });
}

function openBookmark(ref){
  var bm = _bookmarks.items && _bookmarks.items[ref];
  if(!bm) return;
  if(bm.kind==='paper' || bm.kind==='guideline'){
    var loc = bm.locator || {};
    var entry = {id: ref, file_name: loc.file_name, system: loc.system || bm.system || 'General', type: loc.type || bm.type || 'Other', title: bm.title, authors: '', doi: '#', journal: '', date_added: '', year: '', subtopic: ''};
    var live = baseDataset.find(function(d){ return d.file_name === loc.file_name; });
    if(live) entry = live;
    openReader(entry, 'paper');
    return;
  }
  if(bm.kind==='pearl'){
    var loc = bm.locator || {};
    var livePearl = allPearls.find(function(p){ return String(p.id)===String(loc.id); });
    if(livePearl){ openReader(livePearl, 'pearl'); }
    else {
      openReader({id: loc.id, pearl: bm.title, source_paper: '', doi: '', author: '', system: bm.system || 'General', type: bm.type || 'Pearl', remarks: '', file_name: '', topic: '', timestamp: ''}, 'pearl');
    }
    return;
  }
  if(bm.kind==='trial'){
    var slug = (bm.locator && bm.locator.slug) ? bm.locator.slug : String(ref).replace(/^trial:/,'');
    openTrialDetail(slug, [], -1);
    return;
  }
  if(bm.kind==='condensed'){
    var loc = bm.locator || {};
    openCondensedTrialDetail(loc.system || 'General', loc.name || '');
    return;
  }
  if(bm.kind==='flashcard'){
    var loc = bm.locator || {};
    if(!_theoryViewActive()) showView('theory');
    if(loc.card){
      var tRef = theoryDeckFromCardId(loc.card);
      if(tRef){ openTheoryDeck(tRef.deck.id, tRef.idx); return; }
    }
    openTheoryDeck(loc.deck || '', typeof loc.cardIdx==='number' ? loc.cardIdx : 0);
    return;
  }
  if(bm.kind==='note'){
    var loc = bm.locator || {};
    if(!_theoryViewActive()) showView('theory');
    if(loc.noteId){ openTheoryNote(loc.noteId); return; }
    var nId = String(ref).replace(/^note:/,'');
    if(nId) openTheoryNote(nId);
    return;
  }
}

function renderFolderSwatches(active){
  var row = document.getElementById('bookmarksNewFolderColors');
  if(!row) return;
  row.innerHTML = BM_FOLDER_COLORS.map(function(c){
    return '<button type="button" class="folder-swatch'+(c===active?' active':'')+'" data-bm-color="'+c+'" style="background:'+c+'" aria-label="Color '+c+'"></button>';
  }).join('');
}

function bmCardHTML(bm){
  var kindLabel = {paper:'Paper', guideline:'Guideline', pearl:'Pearl', trial:'Trial', condensed:'Condensed Trial', flashcard:'Flashcard', note:'Theory Note'}[bm.kind] || bm.kind;
  var folderOpts = '<option value="">No folder</option>';
  Object.keys(_bookmarks.folders||{}).forEach(function(fid){
    folderOpts += '<option value="'+escapeHtml(fid)+'"'+(bm.folder===fid?' selected':'')+'>'+escapeHtml(_bookmarks.folders[fid].name)+'</option>';
  });
  var dispTitle = String(bm.title||bm.ref);
  if(dispTitle.length>140) dispTitle = dispTitle.substring(0,140)+'&hellip;';
  var tags = (bm.tags||[]).map(function(t){ return '<span class="bm-tag">#'+escapeHtml(t)+'</span>'; }).join('');
  return '<div class="bm-card">'+
    '<button class="bm-card-top" data-bookmark-open="'+escapeHtml(bm.ref)+'" role="button" tabindex="0">'+
      '<div style="flex:1;min-width:0">'+
        '<div style="margin-bottom:6px">'+pillHTML(bm.system||'General', (bm.system||'General')+' &middot; '+kindLabel)+'</div>'+
        '<div class="bm-title">'+escapeHtml(dispTitle)+'</div>'+
        '<div class="bm-meta">'+(bm.type?escapeHtml(bm.type):'')+'</div>'+
      '</div>'+
      '<span class="bm-del" style="font-size:1.1rem">&#8250;</span>'+
    '</button>'+
    '<div class="bm-card-actions">'+
      '<select data-bookmark-folder="'+escapeHtml(bm.ref)+'" title="Move to folder">'+folderOpts+'</select>'+
      '<input class="bm-tags-input" data-bookmark-tags="'+escapeHtml(bm.ref)+'" placeholder="Tags: sepsis, exam" value="'+escapeHtml((bm.tags||[]).join(', '))+'" autocomplete="off">'+
      '<span style="flex:1"></span>'+
      '<button class="bm-del" data-bookmark-del="'+escapeHtml(bm.ref)+'" title="Remove bookmark">&times;</button>'+
    '</div>'+
    (tags?'<div style="display:flex;gap:5px;flex-wrap:wrap">'+tags+'</div>':'')+
  '</div>';
}

function renderBookmarks(){
  var list = document.getElementById('bookmarksList');
  var foldersRow = document.getElementById('bookmarksFoldersRow');
  if(!list) return;
  var items = _bookmarks.items || {};
  var folders = _bookmarks.folders || {};
  var refs = Object.keys(items);
  var q = (document.getElementById('bookmarksSearch').value||'').toLowerCase().trim();

  var fhtml = '';
  if(Object.keys(folders).length){
    fhtml += '<button class="bookmarks-folder-pill'+( _bookmarksFolderFilter===null ? ' active':'')+'" data-bm-folder-all>All</button>';
    Object.keys(folders).forEach(function(fid){
      var f = folders[fid];
      fhtml += '<button class="bookmarks-folder-pill'+( _bookmarksFolderFilter===fid ? ' active':'')+'" data-bm-folder="'+escapeHtml(fid)+'">'+
        '<span class="fdot" style="background:'+escapeHtml(f.color||'#E8B778')+'"></span>'+escapeHtml(f.name)+'</button>';
      fhtml += '<button class="bm-folder-edit" data-bm-folder-rename="'+escapeHtml(fid)+'" title="Rename folder">&#9998;</button>';
      fhtml += '<button class="bm-folder-edit del" data-bm-folder-del="'+escapeHtml(fid)+'" title="Delete folder">&times;</button>';
    });
  }
  foldersRow.innerHTML = fhtml;

  if(!refs.length){
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#128278;</span><p>No bookmarks yet. Tap the &#128278; button on any paper, pearl, or trial to save it here.</p></div>';
    return;
  }

  var filtered = refs.filter(function(ref){
    var bm = items[ref];
    if(_bookmarksFolderFilter !== null && bm.folder !== _bookmarksFolderFilter) return false;
    if(!q) return true;
    var hay = (bm.title||'')+' '+(bm.system||'')+' '+(bm.tags||[]).join(' ');
    return hay.toLowerCase().indexOf(q) !== -1;
  });
  if(!filtered.length){
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#128270;</span><p>No bookmarks match your filters.</p></div>';
    return;
  }

  var groups = {};
  var none = [];
  filtered.forEach(function(ref){ var g = items[ref].folder || null; if(g) (groups[g] = groups[g] || []).push(ref); else none.push(ref); });
  var order = Object.keys(groups).sort(function(a,b){ return ((folders[a]||{}).name||'').localeCompare((folders[b]||{}).name||''); });
  if(none.length) order.unshift('');

  var html = '';
  order.forEach(function(g){
    var label = g ? (folders[g]||{}).name||'Folder' : 'Uncategorized';
    var color = g ? (folders[g]||{}).color||'#E8B778' : 'var(--ink-muted)';
    var groupRefs = g ? groups[g] : none;
    html += '<div class="bm-section-head"><span class="dot" style="background:'+color+'"></span>'+escapeHtml(label)+' <span class="pearl-count">('+groupRefs.length+')</span><span class="bar"></span></div>';
    groupRefs.forEach(function(ref){ html += bmCardHTML(items[ref]); });
  });
  list.innerHTML = html;
}

// =====================================================================
// USERS (admin management)
// =====================================================================
var _usersCache = { users: [], defaults: {} };
function _usersErr(msg){
  var tbody = document.getElementById('usersTableBody');
  var empty = document.getElementById('usersEmpty');
  if(tbody) tbody.innerHTML = '';
  if(empty){ empty.style.display = 'block'; empty.textContent = msg; }
}
function loadUsers(){
  if(!USER_IS_ADMIN) return;
  Promise.all([
    fetch('/api/admin/users').then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); }),
    fetch('/api/admin/users/defaults').then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
  ]).then(function(res){
    _usersCache.users = res[0] || [];
    _usersCache.defaults = res[1] || {};
    renderUsers();
  }).catch(function(e){ _usersErr('Failed to load users: '+e.message); });
}
function _usersFlagLabel(k){ return String(k).replace(/_/g,' '); }
function renderUsers(){
  var grid = document.getElementById('usersDefaultsGrid');
  if(grid && !grid.dataset.built){
    grid.dataset.built = '1';
    var defs = _usersCache.defaults;
    grid.innerHTML = ADMIN_FEATURE_FLAGS.map(function(k){
      var on = defs[k] === true || (defs[k] === undefined && k!=='condensed_trials' && k!=='theory');
      return '<label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;border:1px solid var(--border);padding:4px 10px;border-radius:6px">'+
        '<input type="checkbox" data-def="'+k+'" '+(on?'checked':'')+'> '+_usersFlagLabel(k)+'</label>';
    }).join('');
  }
  var users = _usersCache.users;
  var q = (document.getElementById('usersSearch').value||'').toLowerCase().trim();
  var filtered = q ? users.filter(function(u){
    return (u.email||'').toLowerCase().includes(q) || (u.first_name||'').toLowerCase().includes(q) || (u.last_name||'').toLowerCase().includes(q) || (u.workplace||'').toLowerCase().includes(q);
  }) : users;
  var countEl = document.getElementById('usersCount');
  if(countEl) countEl.textContent = filtered.length + ' of ' + users.length + ' users';
  var empty = document.getElementById('usersEmpty');
  var tbody = document.getElementById('usersTableBody');
  if(empty){ empty.style.display = filtered.length ? 'none' : 'block'; empty.textContent = 'No users found.'; }
  if(!tbody) return;
  tbody.innerHTML = '';
  var defs = _usersCache.defaults;
  filtered.forEach(function(u){
    var feats = u.features || {};
    var tr = document.createElement('tr');
    tr.style.borderTop = '1px solid var(--border)';
    if(u.is_admin) tr.style.background = 'color-mix(in srgb, var(--accent) 6%, transparent)';
    var joined = u.created_at ? String(u.created_at).substring(0,10) : '—';
    var email = String(u.email||'');
    var featHtml = ADMIN_FEATURE_FLAGS.map(function(k){
      var enabled = feats[k] === true || (feats[k] === undefined && defs[k] === true);
      return '<span class="feat-badge '+(enabled?'feat-on':'feat-off')+'" data-flag="'+k+'" data-email="'+encodeURIComponent(email)+'">'+_usersFlagLabel(k)+'</span>';
    }).join(' ');
    tr.innerHTML = '<td style="padding:8px 10px"><strong>'+escapeHtml(email)+'</strong></td>'+
      '<td style="padding:8px 10px">'+escapeHtml((u.first_name||'')+' '+(u.last_name||''))+'</td>'+
      '<td style="padding:8px 10px">'+escapeHtml(u.workplace||'—')+'</td>'+
      '<td style="padding:8px 10px">'+escapeHtml(u.city||'—')+'</td>'+
      '<td style="padding:8px 10px">'+joined+'</td>'+
      '<td style="padding:8px 10px"><span class="admin-toggle '+(u.is_admin?'admin-on':'admin-off')+'" data-email="'+encodeURIComponent(email)+'">'+(u.is_admin?'&#9889; Admin':'Set admin')+'</span></td>'+
      '<td style="padding:8px 10px;display:flex;flex-wrap:wrap;gap:4px">'+featHtml+'</td>'+
      '<td style="padding:8px 10px"><button class="icon-btn-sm" data-del-email="'+encodeURIComponent(email)+'" title="Delete user" style="color:var(--danger,#e5484d)">&#128465;</button></td>';
    tbody.appendChild(tr);
  });
}
document.getElementById('usersSearch').addEventListener('input', renderUsers);
document.addEventListener('click', function(e){
  if(e.target.classList.contains('admin-toggle')){
    var email = decodeURIComponent(e.target.dataset.email);
    var user = _usersCache.users.find(function(u){ return String(u.email)===email; });
    if(!user) return;
    var newVal = !user.is_admin;
    fetch('/api/admin/users/'+encodeURIComponent(email), {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({is_admin: newVal})})
      .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .then(function(){
        user.is_admin = newVal;
        renderUsers();
      }).catch(function(err){ alert('Failed: '+err.message); });
    return;
  }
  if(e.target.classList.contains('feat-badge')){
    var email2 = decodeURIComponent(e.target.dataset.email);
    var flag = e.target.dataset.flag;
    var user2 = _usersCache.users.find(function(u){ return String(u.email)===email2; });
    if(!user2) return;
    var features = user2.features || {};
    features[flag] = !(features[flag] === true);
    user2.features = features;
    fetch('/api/admin/users/'+encodeURIComponent(email2), {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({features: features})})
      .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .then(function(){
        renderUsers();
      }).catch(function(err){ alert('Failed: '+err.message); });
    return;
  }
  if(e.target.dataset.delEmail !== undefined){
    var email3 = decodeURIComponent(e.target.dataset.delEmail);
    if(!confirm('Delete user '+email3+'? This also removes their sessions.')) return;
    fetch('/api/admin/users/'+encodeURIComponent(email3), {method:'DELETE'})
      .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .then(function(){
        _usersCache.users = _usersCache.users.filter(function(u){ return String(u.email)!==email3; });
        renderUsers();
      }).catch(function(err){ alert('Failed: '+err.message); });
    return;
  }
  if(e.target.id === 'usersSaveDefaultsBtn'){
    var updated = {};
    document.querySelectorAll('[data-def]').forEach(function(cb){ updated[cb.dataset.def] = cb.checked; });
    fetch('/api/admin/users/defaults', {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(updated)})
      .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .then(function(d){
        _usersCache.defaults = d;
        var st = document.getElementById('usersDefaultsStatus');
        if(st) st.textContent = 'Saved at ' + new Date().toLocaleTimeString();
      }).catch(function(err){ alert('Failed: '+err.message); });
    return;
  }
});

// =====================================================================
// DISCLAIMER
// =====================================================================
function dismissDisclaimer(){
  document.getElementById('disclaimerOverlay').style.display='none';
  try { localStorage.setItem('hackccm_disclaimer', String(Date.now())); } catch(e){}
}
(function(){
  var last = null;
  try { last = parseInt(localStorage.getItem('hackccm_disclaimer'), 10) || null; } catch(e){}
  var weekMs = 7 * 24 * 60 * 60 * 1000;
  if(showDisclaimer && (!last || Date.now() - last > weekMs)){
    var md = BOOT.disclaimer_text;
    var html = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    document.getElementById('disclaimerText').innerHTML = '<h2>⚠️ Disclaimer</h2><p>'+html+'</p>';
    document.getElementById('disclaimerOverlay').style.display='flex';
  }
})();

// =====================================================================
// SHARE POPUP (grow the platform: ask once per session, weekly cooldown)
// =====================================================================
var sharePopupShown = false;
var sharePopupAttempts = 0;
try { sharePopupAttempts = parseInt(sessionStorage.getItem('hackccm_share_attempts'), 10) || 0; } catch(e){}
function openSharePopup(){
  var pop = document.getElementById('sharePopup');
  if(pop) pop.style.display='flex';
  sharePopupShown = true;
  sharePopupAttempts += 1;
  try { sessionStorage.setItem('hackccm_share_attempts', String(sharePopupAttempts)); } catch(e){}
}
function closeSharePopup(){
  var pop = document.getElementById('sharePopup');
  if(pop) pop.style.display='none';
}
function maybeShowSharePopup(){
  if(sharePopupShown) return;
  var dis = document.getElementById('disclaimerOverlay');
  if(dis && dis.style.display === 'flex') return;
  var last = null;
  try { last = parseInt(localStorage.getItem('hackccm_share'), 10) || null; } catch(e){}
  var weekMs = 7 * 24 * 60 * 60 * 1000;
  if(last && Date.now() - last < weekMs) return;
  if(sharePopupAttempts >= 4) return;
  openSharePopup();
}
function shareCurrentPage(){
  var url = window.location.href;
  var recordAsked = function(){
    try { localStorage.setItem('hackccm_share', String(Date.now())); } catch(e){}
  };
  if(navigator.share){
    navigator.share({ title: document.title, url: url }).then(recordAsked).catch(function(){});
  } else {
    var done = function(){
      recordAsked();
      closeSharePopup();
    };
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(url).then(done).catch(function(){ alert('Copy failed - share manually: '+url); });
    } else {
      var ta = document.createElement('textarea');
      ta.value = url;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch(e){}
      document.body.removeChild(ta);
      done();
    }
  }
}
var sharePopupShareBtn = document.getElementById('sharePopupShare');
if(sharePopupShareBtn) sharePopupShareBtn.addEventListener('click', shareCurrentPage);
var sharePopupFeedbackBtn = document.getElementById('sharePopupFeedback');
if(sharePopupFeedbackBtn) sharePopupFeedbackBtn.addEventListener('click', function(){ closeSharePopup(); window.open(BOOT.feedback_form_url, '_blank'); });
var sharePopupLaterBtn = document.getElementById('sharePopupLater');
if(sharePopupLaterBtn) sharePopupLaterBtn.addEventListener('click', function(){
  closeSharePopup();
  try { localStorage.setItem('hackccm_share', String(Date.now())); } catch(e){}
});
var sharePopupBackdrop = document.getElementById('sharePopupBackdrop');
if(sharePopupBackdrop) sharePopupBackdrop.addEventListener('click', closeSharePopup);
setTimeout(function(){ maybeShowSharePopup(); }, 45000);
setInterval(function(){ maybeShowSharePopup(); }, 60000);

// =====================================================================
// EVENT WIRING (direct listeners for static elements)
// =====================================================================
document.getElementById('logo').addEventListener('click', function(){ showView('home'); });
document.getElementById('logo').addEventListener('keydown', function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); showView('home'); } });
document.getElementById('hamburgerBtn').addEventListener('click', openDrawer);
document.getElementById('drawerBackdrop').addEventListener('click', closeDrawer);
document.getElementById('searchTrigger').addEventListener('click', openSearch);
document.getElementById('closeSearchBtn').addEventListener('click', closeSearch);
document.getElementById('searchBackdrop').addEventListener('click', closeSearch);
document.getElementById('globalSearchInput').addEventListener('input', function(e){ renderSearchResults(e.target.value); });
document.getElementById('themeBtn').addEventListener('click', function(){
  var cur = document.documentElement.getAttribute('data-theme');
  setTheme(THEMES[(THEMES.indexOf(cur)+1) % THEMES.length]);
});
function doLogout(){ fetch('/api/logout',{method:'POST'}).then(function(){ window.location.reload(); }); }
document.getElementById('headerLogout').addEventListener('click', doLogout);
document.getElementById('drawerLogout').addEventListener('click', function(){ closeDrawer(); doLogout(); });
document.getElementById('filterToggleBtn').addEventListener('click', openSheet);
document.getElementById('guidelinesFilterToggleBtn').addEventListener('click', openSheet);
document.getElementById('sheetBackdrop').addEventListener('click', closeSheet);

// Related content panel controls
document.getElementById('relatedClose').addEventListener('click', closeRelatedPanel);
document.getElementById('relatedOverlay').addEventListener('click', function(e){ if(e.target===e.currentTarget) closeRelatedPanel(); });
document.addEventListener('click', function(e){
  var openBtn = e.target.closest('[data-open-related]');
  if(openBtn){ openRelatedPanel(openBtn.getAttribute('data-open-related')); return; }
  var reasonChip = e.target.closest('[data-related-reason]');
  if(reasonChip){ _relatedActiveReason = reasonChip.getAttribute('data-related-reason'); renderRelatedReasonBar(); renderRelatedRows(); return; }
  var goBtn = e.target.closest('[data-related-go]');
  if(goBtn){ relatedGoTo(goBtn.getAttribute('data-related-go')); return; }
  var pearlBtn = e.target.closest('[data-related-pearl]');
  if(pearlBtn){
    var pl = allPearls.find(function(p){ return String(p.id)===pearlBtn.getAttribute('data-related-pearl'); });
    if(pl){ closeRelatedPanel(); openReader(pl, 'pearl'); }
    return;
  }
});
document.addEventListener('keydown', function(e){
  if(e.key==='Escape' && document.getElementById('relatedOverlay').classList.contains('open')) closeRelatedPanel();
});
document.getElementById('bookmarksSearch').addEventListener('input', renderBookmarks);
document.getElementById('theorySearch').addEventListener('input', function(){
  clearTimeout(_theorySearchTimers.decks);
  _theorySearchTimers.decks = setTimeout(function(){
    renderTheoryDecks();
    _theoryReplace();
  }, 200);
});
document.getElementById('theoryNotesSearch').addEventListener('input', function(){
  clearTimeout(_theorySearchTimers.notes);
  _theorySearchTimers.notes = setTimeout(function(){
    renderTheoryNotes();
    _theoryReplace();
  }, 200);
});
document.getElementById('bookmarksNewFolderBtn').addEventListener('click', function(){
  document.getElementById('bookmarksNewFolderRow').classList.add('show');
  renderFolderSwatches(_bmNewFolderColor);
  document.getElementById('bookmarksNewFolderName').focus();
});
document.getElementById('bookmarksCancelFolderBtn').addEventListener('click', function(){
  document.getElementById('bookmarksNewFolderRow').classList.remove('show');
  document.getElementById('bookmarksNewFolderName').value = '';
});
document.getElementById('bookmarksCreateFolderBtn').addEventListener('click', createBookmarkFolder);
document.getElementById('bookmarksNewFolderName').addEventListener('keydown', function(e){ if(e.key==='Enter') createBookmarkFolder(); });
document.getElementById('papersSearch').addEventListener('input', renderPapers);
document.getElementById('papersSort').addEventListener('change', renderPapers);
document.getElementById('guidelinesSearch').addEventListener('input', renderGuidelines);
document.getElementById('guidelinesSort').addEventListener('change', renderGuidelines);
document.getElementById('pearlsSearch').addEventListener('input', function(){ pearlsShown = pearlsPageSize; renderPearls(); });
document.getElementById('pearlsSort').addEventListener('change', renderPearls);
document.getElementById('loadMorePearls').addEventListener('click', function(){ pearlsShown += pearlsPageSize; renderPearls(); });
document.getElementById('serendipityBtn').addEventListener('click', openSerendipityModal);
document.getElementById('closeReader').addEventListener('click', function(){
  if(_readerHistoryStack.length>0){
    var prev = _readerHistoryStack.pop();
    openReader(prev.entry, prev.kind);
  } else {
    history.back();
  }
});
document.getElementById('readerBackdrop').addEventListener('click', function(){ if(_readerHistoryStack.length>0){ _readerHistoryStack = []; } history.back(); });
document.getElementById('readerBody').addEventListener('scroll', function(){
  var pct = this.scrollTop / (this.scrollHeight - this.clientHeight) * 100;
  document.getElementById('readerProgress').style.width = Math.min(100, Math.max(0, pct)) + '%';
});
document.getElementById('scrollTopBtn').addEventListener('click', function(){ window.scrollTo({top:0,behavior:'smooth'}); });
document.getElementById('specPapersSort').addEventListener('change', function(){
  var specViewTitle = document.getElementById('specViewTitle').textContent;
  if(specViewTitle) renderSpecialty(specViewTitle);
});
document.getElementById('specGuidelinesSort').addEventListener('change', function(){
  var specViewTitle = document.getElementById('specViewTitle').textContent;
  if(specViewTitle) renderSpecialty(specViewTitle);
});
window.addEventListener('scroll', function(){
  document.getElementById('scrollTopBtn').classList.toggle('visible', window.scrollY>400);
});
// =====================================================================
// GLOBAL BACK NAVIGATOR
// Browser back/forward restores the previous view (or closes an overlay).
// Every user-gesture navigation records one history entry via navPushState;
// 'reader' is an overlay marker whose restore just re-shows the view below.
// =====================================================================
function navPushState(v){
  var cur = history.state;
  if(cur && cur.v===v){ history.replaceState({v:v}, ''); }
  else { history.pushState({v:v}, ''); }
}
function closeAllOverlays(){
  closeReader(); closeRelatedPanel(); closeDrawer(); closeSheet(); closeSearch(); closeWhatsNew();
  document.body.classList.remove('ai-open');
}
window.addEventListener('popstate', function(e){
  var s = e.state || {};
  if(s.t===1){
    _restoring = true;
    try { _applyTheoryDeepLink(new URLSearchParams(window.location.search)); } catch(err){}
    _restoring = false;
    return;
  }
  closeAllOverlays();
  var v = s.v;
  if(v===undefined){ showView('home'); return; }
  showView(v);
});
document.getElementById('aiFab').addEventListener('click', function(){ document.body.classList.toggle('ai-open'); });
document.getElementById('subscribeBtn').addEventListener('click', function(){
  showToast('Coming soon — redirecting to Google Form for now.');
  window.open(BOOT.subscribe_form_url, '_blank');
});
document.getElementById('unsubscribeBtn').addEventListener('click', function(){
  showToast('Coming soon — redirecting to Google Form for now.');
  window.open(BOOT.unsubscribe_form_url, '_blank');
});
document.getElementById('feedbackBtn').addEventListener('click', function(){
  window.open(BOOT.feedback_form_url, '_blank');
});

// Trial filter/clear buttons
var trialFilterBtn = document.getElementById('trialFilterBtn');
if(trialFilterBtn) trialFilterBtn.addEventListener('click', filterTrials);
var trialClearBtn = document.getElementById('trialClearBtn');
if(trialClearBtn) trialClearBtn.addEventListener('click', clearTrialFilters);
// Condensed filter/clear buttons
var condFilterBtn = document.getElementById('condensedFilterBtn');
if(condFilterBtn) condFilterBtn.addEventListener('click', filterCondensed);
var condClearBtn = document.getElementById('condensedClearBtn');
if(condClearBtn) condClearBtn.addEventListener('click', clearCondensedFilters);
// Trial detail back button
var trialDetailBack = document.getElementById('trialDetailBackBtn');
if(trialDetailBack) trialDetailBack.addEventListener('click', function(){ history.back(); });

// What's New overlay
var whatsNewBtn = document.getElementById('whatsNewBtn');
if(whatsNewBtn) whatsNewBtn.addEventListener('click', openWhatsNew);
var whatsNewOverlayEl = document.getElementById('whatsNewOverlay');
if(whatsNewOverlayEl) whatsNewOverlayEl.addEventListener('click', function(e){
  if(e.target === whatsNewOverlayEl || e.target.closest('#whatsNewClose')){ closeWhatsNew(); return; }
  var wnChip = e.target.closest('[data-wn-filter]');
  if(wnChip){ _wnFilter = wnChip.dataset.wnFilter; renderWhatsNewChips(); renderWhatsNew(); return; }
  if(e.target.closest('[data-open-paper],[data-open-pearl],[data-theory-note],[data-theory-deck]')){ closeWhatsNew(); }
});

// =====================================================================
// DELEGATED EVENT HANDLING (for dynamically rendered elements)
// =====================================================================
document.addEventListener('click', function(e){
  if(e.target.closest('[data-close-search]')) closeSearch();

  /* Re-open disclaimer from hamburger */
  if(e.target.closest('[data-open-disclaimer]')){
    closeDrawer();
    var md = BOOT.disclaimer_text;
    var html = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
    document.getElementById('disclaimerText').innerHTML = '<h2>⚠️ Disclaimer</h2><p>'+html+'</p>';
    document.getElementById('disclaimerOverlay').style.display='flex';
    return;
  }

  var openPaperBtn = e.target.closest('[data-open-paper]');
  if(openPaperBtn){ var id=openPaperBtn.dataset.openPaper; var paper=baseDataset.find(function(x){ return x.id===id; }); if(paper) openReader(paper,'paper'); return; }

  var openPearlBtn = e.target.closest('[data-open-pearl]');
  if(openPearlBtn){
    var pid = openPearlBtn.dataset.openPearl;
    if(pid==='day'){ if(_pearlOfDay) openReader(_pearlOfDay,'pearl'); return; }
    var pearl = allPearls.find(function(x){ return String(x.id)===String(pid); });
    if(pearl) openReader(pearl,'pearl'); return;
  }

  var navBtn = e.target.closest('[data-view]');
  if(navBtn){ if(showView(navBtn.dataset.view)) navPushState(navBtn.dataset.view); return; }

  var specTile = e.target.closest('[data-spec-jump]');
  if(specTile){ jumpToSpecialty(specTile.dataset.specJump); return; }

  var pearlChip = e.target.closest('[data-pearl-chip]');
  if(pearlChip){
    var name = pearlChip.dataset.pearlChip;
    if(activePearlSpecs.has(name)) activePearlSpecs.delete(name); else activePearlSpecs.add(name);
    pearlsShown = pearlsPageSize; renderPearlChips(); renderPearls(); return;
  }
  if(e.target.closest('[data-pearl-chip-reset]')){
    activePearlSpecs = new Set(SPECS.map(function(s){ return s.name; }));
    pearlsShown = pearlsPageSize; renderPearlChips(); renderPearls(); return;
  }
  if(e.target.closest('[data-pearl-chip-uncheck]')){
    activePearlSpecs = new Set();
    pearlsShown = pearlsPageSize; renderPearlChips(); renderPearls(); return;
  }

  /* Subtopic chips in specialty view */
  var subtopicBtn = e.target.closest('[data-subtopic]');
  if(subtopicBtn){
    activeSubtopic = subtopicBtn.dataset.subtopic;
    var specName = document.getElementById('specViewTitle').textContent;
    if(specName) renderSpecialty(specName);
    return;
  }
  if(e.target.closest('[data-subtopic-clear]')){
    activeSubtopic = null;
    var specName = document.getElementById('specViewTitle').textContent;
    if(specName) renderSpecialty(specName);
    return;
  }

  /* Pearl navigation (prev/next) */
  var pearlNav = e.target.closest('[data-pearl-nav]');
  if(pearlNav){
    var step = pearlNav.dataset.pearlNav==='next' ? 1 : -1;
    var targetIdx = _currentPearlIndex + step;
    if(targetIdx>=0 && targetIdx<_currentPearlList.length){
      _readerHistoryStack = [];
      openReader(_currentPearlList[targetIdx], 'pearl');
    }
    return;
  }

  /* Serendipity Mode navigation (prev/next) */
  var serendipityNav = e.target.closest('[data-serendipity-nav]');
  if(serendipityNav){
    navigateSerendipity(serendipityNav.dataset.serendipityNav);
    return;
  }

  /* Open pearl article in same reader */
  var openArticle = e.target.closest('[data-open-pearl-article]');
  if(openArticle){
    var pearlId = openArticle.dataset.openPearlArticle;
    var pearl = allPearls.find(function(p){ return String(p.id)===String(pearlId); });
    if(pearl && pearl.file_name){
      var pdfFn = pearl.file_name.replace(/\.json$/, '.pdf');
      var paper = baseDataset.find(function(d){ return d.file_name === pdfFn; });
      if(paper){
        _readerHistoryStack.push({kind:'pearl', entry:pearl});
        openReader(paper, 'paper');
      }
    }
    return;
  }

  /* Apply filters button */
  var applyBtn = e.target.closest('.apply-btn');
  if(applyBtn){
    var container = applyBtn.closest('#filterPanelDesktop, #filterSheetBody, #filterPanelGuidelines');
    if(container){
      SPECS.forEach(function(s){ var el = container.querySelector('[data-spec="'+s.name+'"]'); if(el) filterState.specialties[s.name] = el.checked; });
      renderFilterCheckboxes();
    }
    var activeView = document.querySelector('.view.active');
    if(activeView){
      if(activeView.id==='view-papers') renderPapers();
      if(activeView.id==='view-guidelines') renderGuidelines();
    }
    if(container && container.id==='filterSheetBody') closeSheet();
    return;
  }

  var resetBtn = e.target.closest('.filter-reset');
  if(resetBtn){
    SPECS.forEach(function(s){ filterState.specialties[s.name] = true; });
    renderFilterCheckboxes();
    var activeView = document.querySelector('.view.active');
    if(activeView){
      if(activeView.id==='view-papers') renderPapers();
      if(activeView.id==='view-guidelines') renderGuidelines();
    }
    return;
  }

  /* specialty panel toggle */
  var specPanelHead = e.target.closest('.spec-panel-head');
  if(specPanelHead){
    var panel = specPanelHead.closest('.spec-panel');
    if(panel) panel.classList.toggle('open');
    return;
  }
  var collapseBtn = e.target.closest('.spec-panel .collapse-btn');
  if(collapseBtn){
    var panel = collapseBtn.closest('.spec-panel');
    if(panel) panel.classList.remove('open');
    return;
  }

  var readerFontBtn = e.target.closest('[data-reader-font]');
  if(readerFontBtn){
    document.querySelector('.reader-body').style.setProperty('--reader-fs', readerFontBtn.dataset.readerFont+'rem');
    document.querySelectorAll('#readerFontChips .size-chip').forEach(function(c){ c.classList.toggle('active', c===readerFontBtn); });
    return;
  }

  var fontChip = e.target.closest('[data-font-px]');
  if(fontChip){ setSiteFontSize(+fontChip.dataset.fontPx); return; }

  var themeChip = e.target.closest('[data-theme-choice]');
  if(themeChip){ setTheme(themeChip.dataset.themeChoice); return; }

  /* Trial specialty grid tile */
  var trialSpecTile = e.target.closest('[data-trial-spec]');
  if(trialSpecTile){ renderTrialsSpecialty(trialSpecTile.dataset.trialSpec); return; }

  /* Condensed trial spec tile */
  var condensedSpecTile = e.target.closest('[data-condensed-spec]');
  if(condensedSpecTile){ renderCondensedSystem(condensedSpecTile.dataset.condensedSpec); return; }

  /* Open condensed trial detail */
  var condensedCard = e.target.closest('[data-open-condensed]');
  if(condensedCard){
    var parts = condensedCard.dataset.openCondensed.split('/');
    openCondensedTrialDetail(parts[0], parts[1]);
    return;
  }

  /* Open trial detail from card */
  var trialCard = e.target.closest('[data-open-trial]');
  if(trialCard){
    var slug = trialCard.dataset.openTrial;
    var idx = parseInt(trialCard.dataset.idx, 10);
    if(!isNaN(idx) && idx>=0 && idx<_currentTrialList.length){
      openTrialDetail(slug, _currentTrialList, idx);
    } else {
      openTrialDetail(slug, [], -1);
    }
    return;
  }

  /* Trials subtopic chips */
  var trialSubBtn = e.target.closest('#trialsSubtopicChips .subtopic-chip');
  if(trialSubBtn){
    document.querySelectorAll('#trialsSubtopicChips .subtopic-chip').forEach(function(c){ c.classList.remove('active'); });
    trialSubBtn.classList.add('active');
    var st = trialSubBtn.dataset.st || '';
    var name = document.getElementById('trialsSpecTitle').textContent;
    _filterTrialsBySpecialty(name, st);
    return;
  }

  /* Close trial overlays on backdrop click */
  if(e.target.matches('.trial-overlay-backdrop')){
    e.target.style.display = 'none';
  }

  /* Bookmarks */
  var bmToggle = e.target.closest('[data-bookmark-toggle]');
  if(bmToggle){ toggleBookmark(bmToggle.dataset.bookmarkToggle); return; }

  var bmOpen = e.target.closest('[data-bookmark-open]');
  if(bmOpen){ openBookmark(bmOpen.dataset.bookmarkOpen); return; }

  var bmDel = e.target.closest('[data-bookmark-del]');
  if(bmDel){ removeBookmark(bmDel.dataset.bookmarkDel); return; }

  var bmFolderAll = e.target.closest('[data-bm-folder-all]');
  if(bmFolderAll){ _bookmarksFolderFilter = null; renderBookmarks(); return; }

  var bmFolder = e.target.closest('[data-bm-folder]');
  if(bmFolder){ _bookmarksFolderFilter = bmFolder.dataset.bmFolder; renderBookmarks(); return; }

  var bmFolderRename = e.target.closest('[data-bm-folder-rename]');
  if(bmFolderRename){ renameBookmarkFolder(bmFolderRename.dataset.bmFolderRename); return; }

  var bmFolderDel = e.target.closest('[data-bm-folder-del]');
  if(bmFolderDel){ deleteBookmarkFolder(bmFolderDel.dataset.bmFolderDel); return; }

  var bmColor = e.target.closest('[data-bm-color]');
  if(bmColor){ _bmNewFolderColor = bmColor.dataset.bmColor; renderFolderSwatches(_bmNewFolderColor); return; }

  /* Theory flashcards */
  var theoryModeBtn = e.target.closest('[data-theory-mode-view]');
  if(theoryModeBtn){
    var tmode = theoryModeBtn.dataset.theoryModeView;
    renderTheoryPane(tmode);
    _theoryPush();
    _focusCrumb();
    return;
  }

  var theoryCrumb = e.target.closest('[data-crumb]');
  if(theoryCrumb){ theoryGoTo(parseInt(theoryCrumb.dataset.crumb,10)||0); return; }

  var theoryFontBtn = e.target.closest('[data-theory-font]');
  if(theoryFontBtn){
    var tscope = theoryFontBtn.dataset.theoryFont;
    var tval = parseFloat(theoryFontBtn.dataset.theoryFontVal)||1;
    try { localStorage.setItem('hackccm_theoryFont_'+tscope, String(tval)); } catch(e){}
    applyTheoryFont(tscope);
    document.querySelectorAll('[data-theory-font="'+tscope+'"]').forEach(function(c){
      c.classList.toggle('active', c===theoryFontBtn);
    });
    return;
  }

  var theoryNoteBtn = e.target.closest('[data-theory-note]');
  if(theoryNoteBtn){
    if(!_theoryViewActive()) showView('theory');
    openTheoryNote(theoryNoteBtn.dataset.theoryNote); return;
  }

  var theoryNoteNavBtn = e.target.closest('[data-theory-note-nav]');
  if(theoryNoteNavBtn){ theoryNoteNav(parseInt(theoryNoteNavBtn.dataset.theoryNoteNav,10)||0); return; }

  var exportNoteBtn = e.target.closest('[data-export-note]');
  if(exportNoteBtn){ window.open('/export/print?'+exportNoteBtn.dataset.exportNote, '_blank', 'noopener'); return; }
  var exportPaperBtn = e.target.closest('[data-export-paper]');
  if(exportPaperBtn){ window.open('/export/print?'+exportPaperBtn.dataset.exportPaper, '_blank', 'noopener'); return; }

  var theoryTableOpen = e.target.closest('[data-theory-table-open]');
  if(theoryTableOpen){ openTheoryTableOverlay(theoryTableOpen); return; }
  var theoryTableClose = e.target.closest('[data-theory-table-close]');
  if(theoryTableClose){ closeTheoryTableOverlay(); return; }
  var theoryTableFit = e.target.closest('[data-theory-table-fit]');
  if(theoryTableFit){ theoryTableToggleFit(); return; }

  var theoryCardSearch = e.target.closest('[data-theory-card]');
  if(theoryCardSearch){
    var tRef = theoryDeckFromCardId(theoryCardSearch.dataset.theoryCard);
    if(tRef){
      if(!_theoryViewActive()) showView('theory');
      openTheoryDeck(tRef.deck.id, tRef.idx);
    }
    return;
  }

  var theoryListOpen = e.target.closest('[data-theory-list-open]');
  if(theoryListOpen && _currentDeck){ openTheoryCardList(_currentDeck.id); return; }

  var theoryDone = e.target.closest('[data-theory-done]');
  if(theoryDone){ theoryStepBackFromStudy(); return; }

  var theoryCardOpen = e.target.closest('[data-theory-card-open]');
  if(theoryCardOpen && _currentDeck){
    _theoryListCollapsed = true;
    renderTheoryCardList();
    openTheoryDeck(_currentDeck.id, theoryCardOpen.dataset.theoryCardOpen, true);
    _theoryStudyFromList = true;
    return;
  }

  var theoryListToggle = e.target.closest('[data-theory-list-toggle]');
  if(theoryListToggle){
    _theoryListCollapsed = !_theoryListCollapsed;
    renderTheoryCardList();
    return;
  }

  var theoryDeckBtn = e.target.closest('[data-theory-deck]');
  if(theoryDeckBtn){ openTheoryDeck(theoryDeckBtn.dataset.theoryDeck, 0); return; }

  var theoryChip = e.target.closest('[data-theory-chip]');
  if(theoryChip){
    var s = theoryChip.dataset.theoryChip;
    if(_theoryActiveSpecs.has(s)) _theoryActiveSpecs.delete(s); else _theoryActiveSpecs.add(s);
    renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return;
  }

  var theoryReset = e.target.closest('[data-theory-chip-reset]');
  if(theoryReset){ _theoryActiveSpecs = new Set(allFlashcardDecks.map(function(d){ return normalizeSpec(d.specialty); })); renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return; }

  var theoryUncheck = e.target.closest('[data-theory-chip-uncheck]');
  if(theoryUncheck){ _theoryActiveSpecs = new Set(); renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return; }

  var theorySavedOnly = e.target.closest('[data-theory-saved-only]');
  if(theorySavedOnly){ _theorySavedOnly = !_theorySavedOnly; renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return; }
  var notesSavedOnly = e.target.closest('[data-notes-saved-only]');
  if(notesSavedOnly){ _notesSavedOnly = !_notesSavedOnly; renderTheoryNotes(); _theoryReplace(); return; }
  var notesSpec = e.target.closest('[data-notes-spec]');
  if(notesSpec){
    var s = notesSpec.getAttribute('data-notes-spec');
    if(_notesActiveSpecs.has(s)) _notesActiveSpecs.delete(s);
    else _notesActiveSpecs.add(s);
    if(!_notesActiveSpecs.size) _notesActiveSubtopic = null;
    else if(_notesActiveSpecs.size>1) _notesActiveSubtopic = null;
    renderTheoryNotes(); _theoryReplace(); return;
  }
  var notesSub = e.target.closest('[data-notes-sub]');
  if(notesSub){
    _notesActiveSubtopic = (_notesActiveSubtopic===notesSub.getAttribute('data-notes-sub')) ? null : notesSub.getAttribute('data-notes-sub');
    renderTheoryNotes(); _theoryReplace(); return;
  }
  var notesClearAll = e.target.closest('[data-notes-clear-all]');
  if(notesClearAll){ _notesSavedOnly = false; _notesActiveSpecs = new Set(); _notesActiveSubtopic = null; renderTheoryNotes(); _theoryReplace(); return; }

  var theorySub = e.target.closest('[data-theory-subtopic]');
  if(theorySub){
    var t = theorySub.dataset.theorySubtopic;
    _theoryActiveSubtopic = (_theoryActiveSubtopic===t) ? null : t;
    renderTheorySubtopicChips(); renderTheoryDecks(); _theoryReplace(); return;
  }

  var theorySubClear = e.target.closest('[data-theory-subtopic-clear]');
  if(theorySubClear){ _theoryActiveSubtopic = null; renderTheorySubtopicChips(); renderTheoryDecks(); _theoryReplace(); return; }

  var theoryTagClear = e.target.closest('[data-theory-tag-clear]');
  if(theoryTagClear && _currentDeck){
    _theoryActiveSubtopic = null;
    _theoryCardOrder = _currentDeck.cards.map(function(c, i){ return i; });
    if(_theoryCardOrder.indexOf(_currentCardIdx)===-1) _currentCardIdx = 0;
    _theoryFlipped = false;
    renderTheoryChips();
    renderTheoryCard();
    _theoryReplace();
    return;
  }

  var theoryNavBtn = e.target.closest('[data-theory-nav]');
  if(theoryNavBtn){ theoryNav(parseInt(theoryNavBtn.dataset.theoryNav,10)||0); return; }

  var theoryDot = e.target.closest('[data-theory-dot]');
  if(theoryDot){
    var tpos = parseInt(theoryDot.dataset.theoryDot,10)||0;
    if(_theoryCardOrder[tpos]!=null){
      _currentCardIdx = _theoryCardOrder[tpos];
      _theoryFlipped = false;
      renderTheoryCard();
      _theoryReplace();
    }
    return;
  }

  var theoryMode = e.target.closest('[data-theory-mode]');
  if(theoryMode){ theorySetViewMode(theoryMode.dataset.theoryMode); return; }

  var theoryFlipInner = e.target.closest('#theoryFlipInner');
  if(theoryFlipInner){ _theoryFlipped = !_theoryFlipped; theoryFlipInner.classList.toggle('flipped', _theoryFlipped); return; }
});

document.addEventListener('change', function(e){
  var container = e.target.closest('#filterPanelDesktop, #filterSheetBody, #filterPanelGuidelines');
  if(container){
    if(e.target.classList.contains('all-check')){
      container.querySelectorAll('[data-spec]').forEach(function(b){ b.checked = e.target.checked; });
    }
    SPECS.forEach(function(s){ var el = container.querySelector('[data-spec="'+s.name+'"]'); if(el) filterState.specialties[s.name] = el.checked; });
    renderFilterCheckboxes();
  }
  var bmFolderSel = e.target.closest('[data-bookmark-folder]');
  if(bmFolderSel){ setBookmarkFolder(bmFolderSel.dataset.bookmarkFolder, e.target.value || null); return; }
  var bmTags = e.target.closest('[data-bookmark-tags]');
  if(bmTags){ setBookmarkTags(bmTags.dataset.bookmarkTags, e.target.value); return; }
});

document.addEventListener('keydown', function(e){
  if(e.key==='Escape'){
    if(_theoryTableOverlayOpen){ closeTheoryTableOverlay(); }
    else if(_theoryStudyVisible()){ theoryStepBackFromStudy(); }
    else if(document.getElementById('theoryCardList') && document.getElementById('theoryCardList').style.display!=='none'){ theoryBackToBrowser(); }
    else if(document.getElementById('theoryNoteReader') && document.getElementById('theoryNoteReader').style.display!=='none'){ theoryNotesBack(); }
    closeSearch(); closeDrawer(); closeSheet(); closeReader(); document.body.classList.remove('ai-open');
  }
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){ e.preventDefault(); openSearch(); }
  if((e.key==='Enter'||e.key===' ')&&e.target.matches('[role="button"]')){ e.preventDefault(); e.target.click(); }
  if(_theoryStudyVisible() && !e.target.matches('input,textarea,select')){
    if(e.key==='ArrowRight'){ theoryNav(1); }
    if(e.key==='ArrowLeft'){ theoryNav(-1); }
  }
});

// =====================================================================
// INIT
// =====================================================================
(function init(){
  // Load saved prefs
  try {
    var savedTheme = localStorage.getItem('hackccm_theme');
    if(savedTheme) setTheme(savedTheme); else setTheme('dim');
    var savedFont = localStorage.getItem('hackccm_fontSize');
    if(savedFont) setSiteFontSize(+savedFont); else setSiteFontSize(16);
  } catch(e){ setTheme('dim'); setSiteFontSize(16); }

  // Hide nav/drawer links for disabled features (admins see all)
  if (!USER_IS_ADMIN) {
    var navFeatureMap = {
      'papers': 'papers',
      'guidelines': 'guidelines',
      'pearls': 'pearls',
      'trials': 'trials',
      'trials-esbicm': 'trials',
      'trials-condensed': 'condensed_trials',
      'trials-specialty': 'trials',
      'trials-detail': 'trials_detail',
      'condensed-system': 'condensed_trials',
      'condensed-detail': 'trials_detail',
      'bookmarks': 'bookmarks',
      'theory': 'theory'
    };
    Object.keys(navFeatureMap).forEach(function(viewName) {
      var feature = navFeatureMap[viewName];
      if (!USER_FEATURES[feature]) {
        document.querySelectorAll('[data-view="' + viewName + '"]').forEach(function(el) {
          el.style.display = 'none';
        });
      }
    });
    // Hide search trigger if search feature is disabled
    if (!USER_FEATURES['search']) {
      var searchEl = document.getElementById('searchTrigger');
      if (searchEl) searchEl.style.display = 'none';
    }
  }

  renderFilterCheckboxes();
  loadBookmarks();
  loadSerendipityHistory();
  showView('home');

  // Deep links + browser history:
  //   ?theory=flashcards[&system=S&subtopic=T&card=<uuid>][&q=..][&saved=1]
  //   ?theory=notes[&note=<file>][&q=..][&saved=1]
  _restoring = true;
  try { _applyTheoryDeepLink(new URLSearchParams(window.location.search)); } catch(e){}
  _restoring = false;
})();
