import glob
import re

widget_code = """
<!-- GLOBAL TRANSLATION WIDGET -->
<div id="google_translate_element" style="display:none;"></div>
<style>
/* Hide the default Google Translate toolbar */
.skiptranslate iframe, .goog-te-banner-frame { display: none !important; }
body { top: 0px !important; }

/* Floating Language Selector */
.global-lang-selector {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 50px;
    padding: 8px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    z-index: 999999;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Inter', sans-serif;
    transition: all 0.3s ease;
}
.global-lang-selector:hover {
    box-shadow: 0 6px 16px rgba(0,0,0,0.15);
    transform: translateY(-2px);
}
.global-lang-selector select {
    border: none;
    background: transparent;
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    cursor: pointer;
    outline: none;
    appearance: none;
    padding-right: 20px;
}
</style>
<div class="global-lang-selector">
    <span style="font-size:16px;">🌐</span>
    <select id="globalLanguageSelect" onchange="changeGlobalLanguage(this.value)">
      <option value="en">English</option>
      <option value="ta">தமிழ் (Tamil)</option>
      <option value="hi">हिन्दी (Hindi)</option>
      <option value="ml">മലയാളം (Malayalam)</option>
      <option value="te">తెలుగు (Telugu)</option>
      <option value="kn">ಕನ್ನಡ (Kannada)</option>
    </select>
    <span style="font-size:10px; position:absolute; right:16px; pointer-events:none;">▼</span>
</div>

<script type="text/javascript">
  function googleTranslateElementInit() {
    new google.translate.TranslateElement({
      pageLanguage: 'en',
      includedLanguages: 'en,ta,hi,ml,te,kn',
      autoDisplay: false
    }, 'google_translate_element');
  }
  
  function changeGlobalLanguage(langCode) {
    document.cookie = `googtrans=/en/${langCode}; path=/`;
    if (location.hostname !== 'localhost') {
        document.cookie = `googtrans=/en/${langCode}; domain=.${location.hostname}; path=/`;
    }
    location.reload();
  }
  
  document.addEventListener("DOMContentLoaded", function() {
    const match = document.cookie.match(/googtrans=\\/en\\/([a-z]{2})/);
    if (match && match[1]) {
      const select = document.getElementById('globalLanguageSelect');
      if(select) select.value = match[1];
    }
  });
</script>
<script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
<!-- /GLOBAL TRANSLATION WIDGET -->
"""

files = glob.glob('templates/*.html')
count = 0
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'GLOBAL TRANSLATION WIDGET' not in content and '</body>' in content:
        # Inject right before </body>
        new_content = content.replace('</body>', f"{widget_code}\n</body>")
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count += 1

print(f"Injected floating widget into {count} files.")
