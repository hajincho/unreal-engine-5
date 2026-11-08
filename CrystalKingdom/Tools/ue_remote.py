"""Send a Python file (or statement) to a running CrystalKingdom Unreal Editor via
Python Remote Execution and print its output.

usage:  python ue_remote.py <script.py> [key=value ...]
        python ue_remote.py -c "<python statement>"
Script args are exposed inside the editor as the dict CK_ARGS.
"""
import os
import sys
import time

ENGINE_PY = r"C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
sys.path.insert(0, ENGINE_PY)
import remote_execution as rx  # noqa: E402

PROJECT = "CrystalKingdom"


def find_node(rex, wait=15.0):
    end = time.time() + wait
    while time.time() < end:
        for n in rex.remote_nodes:
            if n.get("project_name") == PROJECT:
                return n
        time.sleep(0.25)
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "-c":
        cmd = sys.argv[2]
    else:
        path = os.path.abspath(sys.argv[1])
        args = dict(a.split("=", 1) for a in sys.argv[2:])
        cmd = (
            "import warnings\n"
            "warnings.simplefilter('ignore', DeprecationWarning)\n"
            "CK_ARGS = %r\n"
            "with open(%r, encoding='utf-8') as _f:\n"
            "    _src = _f.read()\n"
            "exec(compile(_src, %r, 'exec'), "
            "{'__name__': '__main__', 'CK_ARGS': CK_ARGS, '__file__': %r})" % (args, path, path, path)
        )
    rex = rx.RemoteExecution()
    rex.start()
    try:
        node = find_node(rex)
        if not node:
            print("ERROR: no CrystalKingdom editor node found (is the editor running?)")
            return 3
        rex.open_command_connection(node["node_id"])
        res = rex.run_command(cmd, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
        for o in res.get("output", []):
            print(o.get("output", "").rstrip())
        if not res.get("success"):
            print("REMOTE_FAILED:", res.get("result"))
            return 1
        return 0
    finally:
        rex.stop()


if __name__ == "__main__":
    sys.exit(main())
