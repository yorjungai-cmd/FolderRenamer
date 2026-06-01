import os
from PyQt6.QtCore import QThread, pyqtSignal

def scan_paths(paths, extensions, scan_subdirs, on_file, cancel_flag) -> int:
    """Pure function — testable without Qt. Returns file count."""
    count = 0
    exts = {e.lower() for e in extensions}
    for path in paths:
        if cancel_flag():
            break
        if os.path.isfile(path):
            if os.path.splitext(path)[1].lower() in exts:
                on_file(os.path.abspath(path))
                count += 1
        elif os.path.isdir(path):
            walker = os.walk(path) if scan_subdirs else [(path, [], os.listdir(path))]
            for root, _dirs, files in walker:
                if cancel_flag():
                    break
                for fname in files:
                    if os.path.splitext(fname)[1].lower() in exts:
                        on_file(os.path.abspath(os.path.join(root, fname)))
                        count += 1
    return count

class ScanWorker(QThread):
    file_found = pyqtSignal(str)
    finished   = pyqtSignal(int)

    def __init__(self, paths: list, extensions: set, scan_subdirs: bool):
        super().__init__()
        self.paths = paths
        self.extensions = extensions
        self.scan_subdirs = scan_subdirs
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        count = scan_paths(
            self.paths, self.extensions, self.scan_subdirs,
            on_file=self.file_found.emit,
            cancel_flag=lambda: self._cancel,
        )
        self.finished.emit(count)
