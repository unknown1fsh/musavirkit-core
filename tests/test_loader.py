import zipfile

from ubl_builder import build

from musavirkit_core.loader import load_invoices


def test_loads_folder_recursively_and_zip(tmp_path):
    (tmp_path / "alt").mkdir()
    (tmp_path / "f1.xml").write_bytes(build(number="A1", uuid="u1"))
    (tmp_path / "alt" / "f2.XML").write_bytes(build(number="A2", uuid="u2"))
    (tmp_path / "not.txt").write_text("yoksay")
    with zipfile.ZipFile(tmp_path / "arsiv.zip", "w") as zf:
        zf.writestr("ic/f3.xml", build(number="A3", uuid="u3"))
        zf.writestr("readme.txt", "yoksay")

    invoices, issues = load_invoices([tmp_path])

    assert issues == []
    assert sorted(i.number for i in invoices) == ["A1", "A2", "A3"]
    zipped = next(i for i in invoices if i.number == "A3")
    assert zipped.source.endswith("arsiv.zip!ic/f3.xml")


def test_unreadable_file_becomes_issue_not_crash(tmp_path):
    (tmp_path / "bozuk.xml").write_bytes(b"<<<")
    (tmp_path / "iyi.xml").write_bytes(build())

    invoices, issues = load_invoices([tmp_path / "bozuk.xml", tmp_path / "iyi.xml"])

    assert len(invoices) == 1
    assert [i.check for i in issues] == ["OKUNAMADI"]
    assert issues[0].source.endswith("bozuk.xml")


def test_missing_path_becomes_issue(tmp_path):
    invoices, issues = load_invoices([tmp_path / "yok.xml"])
    assert invoices == []
    assert [i.check for i in issues] == ["OKUNAMADI"]
