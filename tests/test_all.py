import sys, types, unittest, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(__file__).with_name("all_tests.zip")

def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    with zipfile.ZipFile(BUNDLE) as zf:
        for name in sorted(n for n in zf.namelist() if n.startswith("test_") and n.endswith(".py")):
            modname = "_bundled_" + Path(name).stem
            source = zf.read(name).decode("utf-8")
            module = types.ModuleType(modname)
            module.__file__ = str(ROOT / "tests" / name)
            module.__package__ = ""
            sys.modules[modname] = module
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            suite.addTests(loader.loadTestsFromModule(module))
    return suite
