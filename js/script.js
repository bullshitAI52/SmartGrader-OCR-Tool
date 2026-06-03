document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const markdownEditor = document.getElementById('markdownEditor');
    const previewEditor = document.getElementById('previewEditor');
    const pasteBtn = document.getElementById('pasteBtn');
    const copyBtn = document.getElementById('copyBtn');
    const tutorialModal = document.getElementById('tutorialModal');
    const tutorialBtn = document.getElementById('tutorialBtn');
    const closeTutorial = document.getElementById('closeTutorial');
    const closeTutorialBtn = document.getElementById('closeTutorialBtn');

    // --- Modal Logic ---
    function openModal() { tutorialModal.style.display = "block"; }
    function closeModal() { tutorialModal.style.display = "none"; }

    if (tutorialBtn) tutorialBtn.onclick = openModal;
    if (closeTutorial) closeTutorial.onclick = closeModal;
    if (closeTutorialBtn) closeTutorialBtn.onclick = closeModal;
    window.onclick = function (event) {
        if (event.target == tutorialModal) closeModal();
    }

    // --- Editor Logic ---

    // Auto-render Markdown on input
    markdownEditor.addEventListener('input', function () {
        const markdown = markdownEditor.innerText;
        renderMarkdown(markdown);
    });

    // Paste Button
    if (pasteBtn) {
        pasteBtn.addEventListener('click', async function () {
            try {
                const text = await navigator.clipboard.readText();
                markdownEditor.innerText = text; // or insert at cursor
                renderMarkdown(text);
            } catch (err) {
                console.error('Failed to read clipboard', err);
                alert('请允许访问剪贴板，或直接使用 Ctrl+V 粘贴');
            }
        });
    }

    // Copy Content Button (copies HTML preview content)
    if (copyBtn) {
        copyBtn.addEventListener('click', function () {
            const range = document.createRange();
            range.selectNodeContents(previewEditor);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            document.execCommand('copy');
            alert('内容已复制到剪贴板');
        });
    }

    function renderMarkdown(text) {
        // Use marked.js if available
        if (typeof marked !== 'undefined') {
            try {
                // Configure marked
                // marked.setOptions({ breaks: true, gfm: true }); 
                const html = marked.parse(text);
                // Sanitize if DOMPurify is available
                if (typeof DOMPurify !== 'undefined') {
                    previewEditor.innerHTML = DOMPurify.sanitize(html);
                } else {
                    previewEditor.innerHTML = html;
                }
            } catch (e) {
                console.error("Markdown parsing error:", e);
                previewEditor.innerHTML = text;
            }
        } else {
            previewEditor.innerHTML = "<p style='color:red'>Marked.js library not loaded.</p>" + text;
        }
    }


    // --- Export Logic (Placeholders/Basic Implementation) ---

    // Export Word (HTML with specific headers)
    document.getElementById('exportWordBtn').addEventListener('click', function () {
        const header = "<html xmlns:o='urn:schemas-microsoft-com:office:office' " +
            "xmlns:w='urn:schemas-microsoft-com:office:word' " +
            "xmlns='http://www.w3.org/TR/REC-html40'>" +
            "<head><meta charset='utf-8'><title>Export HTML to Word Document with JavaScript</title></head><body>";
        const footer = "</body></html>";
        const sourceHTML = header + previewEditor.innerHTML + footer;

        const source = 'data:application/vnd.ms-word;charset=utf-8,' + encodeURIComponent(sourceHTML);
        const fileDownload = document.createElement("a");
        document.body.appendChild(fileDownload);
        fileDownload.href = source;
        fileDownload.download = 'document.doc';
        fileDownload.click();
        document.body.removeChild(fileDownload);
    });

    // Simple Image Export using html2canvas
    document.getElementById('exportImageBtn').addEventListener('click', function () {
        if (typeof html2canvas !== 'undefined') {
            html2canvas(previewEditor).then(canvas => {
                const link = document.createElement('a');
                link.download = 'content.png';
                link.href = canvas.toDataURL();
                link.click();
            });
        } else {
            alert('html2canvas library not loaded');
        }
    });

    // Placeholders for Excel and PDF 
    // PDF typically requires jsPDF or printing the page
    document.getElementById('exportPdfBtn').addEventListener('click', function () {
        window.print(); // Simple fallback
    });

    document.getElementById('exportExcelBtn').addEventListener('click', function () {
        // Basic table to excel using SheetJS if available
        const tables = previewEditor.getElementsByTagName('table');
        if (tables.length > 0 && typeof XLSX !== 'undefined') {
            const wb = XLSX.utils.table_to_book(tables[0]);
            XLSX.writeFile(wb, 'data.xlsx');
        } else {
            alert('没有检测到表格，或 XLSX 库未加载');
        }
    });

});
