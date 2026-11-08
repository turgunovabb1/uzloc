import pytest

from uzloc.cli import main


def test_translit_auto_latin_to_cyrillic(capsys):
    assert main(["translit", "Salom", "dunyo"]) == 0
    assert capsys.readouterr().out == "Салом дунё\n"


def test_translit_auto_cyrillic_to_latin(capsys):
    assert main(["translit", "Ўзбекистон"]) == 0
    assert capsys.readouterr().out == "O'zbekiston\n"


def test_translit_forced_target(capsys):
    # Already Latin text stays Latin when --to latin is asked.
    main(["translit", "Toshkent", "--to", "latin"])
    assert capsys.readouterr().out == "Toshkent\n"


def test_translit_file_to_file(tmp_path):
    source = tmp_path / "in.txt"
    target = tmp_path / "out.txt"
    source.write_text("Тошкент шаҳри\nЎзбекистон\n", encoding="utf-8")

    assert main(["translit", "-f", str(source), "-o", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == "Toshkent shahri\nO'zbekiston\n"


def test_detect(capsys):
    assert main(["detect", "Salom", "Салом"]) == 0
    assert capsys.readouterr().out == "mixed\n"


def test_detect_file(tmp_path, capsys):
    source = tmp_path / "in.txt"
    source.write_text("Салом", encoding="utf-8")
    main(["detect", "-f", str(source)])
    assert capsys.readouterr().out == "cyrillic\n"


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "uzloc" in capsys.readouterr().out


def test_unknown_command_fails():
    with pytest.raises(SystemExit):
        main(["fly"])