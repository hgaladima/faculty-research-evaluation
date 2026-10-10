"""Drive a real copy of Excel (Windows only) to recalculate and read the calculator workbook."""
from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

ERRORS = {-2146826281: "#DIV/0!", -2146826246: "#N/A", -2146826259: "#NAME?", -2146826288: "#NULL!",
          -2146826252: "#NUM!", -2146826265: "#REF!", -2146826273: "#VALUE!"}


@contextmanager
def excel():
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    app = win32com.client.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    try:
        yield app
    finally:
        app.Quit()
        pythoncom.CoUninitialize()


@contextmanager
def open_copy(app, source: Path):
    """Open a temporary copy with every sheet unprotected, so the original is never touched."""
    folder = Path(tempfile.mkdtemp(prefix="fre_excel_"))
    target = folder / Path(source).name
    shutil.copy(source, target)
    book = app.Workbooks.Open(str(target))
    try:
        for sheet in book.Worksheets:
            sheet.Unprotect()
        yield book
    finally:
        book.Close(SaveChanges=False)
        shutil.rmtree(folder, ignore_errors=True)


def formula_errors(book) -> list[str]:
    """Every cell holding an Excel error value, as 'Sheet!A1 #NAME?'."""
    found = []
    for sheet in book.Worksheets:
        used = sheet.UsedRange
        values = used.Value
        if not isinstance(values, tuple):
            values = ((values,),)
        for i, row in enumerate(values):
            for j, value in enumerate(row):
                if isinstance(value, int) and value in ERRORS:
                    found.append(f"{sheet.Name}!{used.Cells(i + 1, j + 1).Address.replace('$', '')} {ERRORS[value]}")
    return found


def recalculate_and_save(path: Path) -> list[str]:
    """Recalculate the workbook in Excel, store the calculated values in the file, and return any formula errors."""
    with excel() as app:
        book = app.Workbooks.Open(str(Path(path).resolve()))
        try:
            app.CalculateFullRebuild()
            errors = formula_errors(book)
            book.Save()
        finally:
            book.Close(SaveChanges=False)
    return errors
