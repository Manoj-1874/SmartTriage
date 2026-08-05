import glob
import re

new_widget_code = """<!-- GLOBAL TRANSLATION WIDGET -->
<div id="google_translate_element" style="display:none;"></div>
<style>
.skiptranslate iframe, .goog-te-banner-frame { display: none !important; }
body { top: 0px !important; }
.global-lang-selector {
    position: fixed;
    bottom: 20px;
    right: 80px;
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
      includedLanguages: 'ta,hi,ml,te,kn',
      layout: google.translate.TranslateElement.InlineLayout.SIMPLE,
      autoDisplay: false
    }, 'google_translate_element');
    
    // After initialization, check if we need to sync the combo box based on cookie
    setTimeout(function() {
        var match = document.cookie.match(/googtrans=\\/en\\/([a-z]{2})/);
        if (match && match[1]) {
            var gtSelect = document.querySelector('.goog-te-combo');
            if (gtSelect && gtSelect.value !== match[1]) {
                gtSelect.value = match[1];
                gtSelect.dispatchEvent(new Event('change'));
            }
        }
    }, 1000);
  }

  function changeGlobalLanguage(langCode) {
    // Clear all possible old googtrans cookies to avoid conflicts
    var domain = location.hostname;
    document.cookie = "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    document.cookie = "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; domain=" + domain + "; path=/;";
    document.cookie = "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; domain=." + domain + "; path=/;";
    
    if (langCode === 'en') {
        // To restore original English, trigger the restore button in the hidden banner if possible
        var iframe = document.querySelector('.goog-te-banner-frame');
        if (iframe) {
            var innerDoc = iframe.contentDocument || iframe.contentWindow.document;
            var restoreBtn = innerDoc.getElementById(':1.restore') || innerDoc.querySelector('button');
            if(restoreBtn) restoreBtn.click();
        }
        location.reload();
        return;
    }
    
    // Set new cookie precisely
    var expiry = new Date();
    expiry.setTime(expiry.getTime() + (30 * 24 * 60 * 60 * 1000));
    document.cookie = "googtrans=/en/" + langCode + ";expires=" + expiry.toUTCString() + ";path=/;domain=" + (domain === 'localhost' ? '' : '.' + domain);

    // Force trigger translation directly without reloading
    var gtSelect = document.querySelector('.goog-te-combo');
    if (gtSelect) {
        gtSelect.value = langCode;
        gtSelect.dispatchEvent(new Event('change'));
    } else {
        location.reload();
    }
  }

  document.addEventListener("DOMContentLoaded", function() {
    const match = document.cookie.match(/googtrans=\\/en\\/([a-z]{2})/);
    if (match && match[1]) {
      const select = document.getElementById('globalLanguageSelect');
      if(select) select.value = match[1];
    }
  });
</script>
<script type="text/javascript" src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
<!-- /GLOBAL TRANSLATION WIDGET -->"""

files = glob.glob('templates/*.html')
count = 0
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '<!-- GLOBAL TRANSLATION WIDGET -->' in content:
        # Regex replace the whole block
        new_content = re.sub(
            r'<!-- GLOBAL TRANSLATION WIDGET -->.*?<!-- /GLOBAL TRANSLATION WIDGET -->', 
            new_widget_code, 
            content, 
            flags=re.DOTALL
        )
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count += 1

print(f"Updated translation widget in {count} files.")
