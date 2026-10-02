// Code sections keep the browser's default scrollbars (overlay scrollbars,
// shown only while scrolling, where the system uses them). The theme styles
// every scrollbar of the site with global ::-webkit-scrollbar rules, and any
// styled ::-webkit-scrollbar is drawn always visible: CSS cannot exempt
// elements from a global rule, so scope the theme's rules here to the elements
// outside the code sections.
const CODE_SECTIONS = ".code-frame, .doc-signature, .jupyter-wrapper .jp-CodeCell";

function scopeScrollbarRules(rules) {
	for (const rule of rules) {
		if (rule instanceof CSSStyleRule) {
			if (rule.selectorText.startsWith("::-webkit-scrollbar")) {
				rule.selectorText = `:not(:is(${CODE_SECTIONS}) *)${rule.selectorText}`;
			}
		} else if (rule.cssRules !== undefined) {
			// @layer, @media, @supports blocks
			scopeScrollbarRules(rule.cssRules);
		}
	}
}

for (const sheet of document.styleSheets) {
	let rules;
	try {
		rules = sheet.cssRules;
	} catch {
		// a cross-origin sheet cannot be read, and is not the theme's
		continue;
	}
	scopeScrollbarRules(rules);
}
