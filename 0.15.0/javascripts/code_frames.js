// Copy buttons of the code frames built by mkdocs_extensions/code_frames.py:
// copy the code panel (not the output), then show the "Copied!" notice in place
// of the icon for a second, like the notebook cells.
document.addEventListener("click", (event) => {
	const button = event.target.closest(".code-frame-copy");
	if (button === null) {
		return;
	}
	const code = button.closest(".code-frame").querySelector(".code-frame-panel code");
	navigator.clipboard.writeText(code.textContent.replace(/\n$/, "")).then(() => {
		const notice = button.querySelector(".code-frame-copied");
		notice.hidden = false;
		setTimeout(() => {
			notice.hidden = true;
		}, 1000);
	});
});
