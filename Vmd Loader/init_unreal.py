import os
import sys
import unreal

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

try:
    import Menu
    Menu.register()
except Exception as e:
    unreal.log_error(str(e))
