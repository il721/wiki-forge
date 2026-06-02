"""Discover plugin files, instantiate them, and isolate failures."""
import importlib.util
import inspect
import traceback
from pathlib import Path

from cockpit.plugin import Plugin


class PluginHost:
    def __init__(self, plugin_dirs, context_factory, log=print):
        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        self.context_factory = context_factory
        self.log = log
        self.loaded = []   # list[(plugin_instance, context)]
        self.failed = []   # list[(name, traceback_str)]

    def _classes_in(self, path):
        spec = importlib.util.spec_from_file_location(f"wf_plugin_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        found = []
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin and obj.__module__ == mod.__name__:
                found.append(obj)
        return found

    def discover(self):
        classes = []
        for d in self.plugin_dirs:
            if not d.exists():
                continue
            for f in sorted(d.rglob("*.py")):
                if f.name.startswith("_"):
                    continue
                try:
                    classes.extend(self._classes_in(f))
                except Exception:
                    self.failed.append((str(f), traceback.format_exc()))
        return classes

    def load_all(self):
        for cls in self.discover():
            try:
                inst = cls()
                ctx = self.context_factory(inst)
                inst.activate(ctx)
                self.loaded.append((inst, ctx))
            except Exception:
                self.failed.append((cls.__name__, traceback.format_exc()))
                self.log(f"[plugin-host] failed to load {cls.__name__}")
        return self.loaded
