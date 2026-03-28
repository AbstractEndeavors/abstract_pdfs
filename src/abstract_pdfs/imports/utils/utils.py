from .imports import *
def get_dict(obj):
    if not isinstance(obj,dict):
        try:
            obj = obj.to_dict()
        except Exception as e:
            logger.info(f"ERROR in generators.py via {obj}: {e}")
    return obj
def fill_nulls(target, source):
    """
    Recursively fill None/missing values in target from source.
    Returns (target, changed) where changed is True if anything was updated.
    """
    changed = False
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            _, child_changed = fill_nulls(existing, value)
            changed = changed or child_changed
        elif existing is None and value is not None:
            target[key] = value
            changed = True
    return target, changed
def update_json(path,source):
    exists = os.path.isfile(path)
    source = get_dict(source)
    if exists:
        data = safe_load_from_json(path)
        target, changed=fill_nulls(data, source)
        if changed:
            safe_dump_to_json(file_path=path, data=target)
        return target
    else:
       safe_dump_to_json(file_path=path, data=source)
       return source

def get_page_num(i):
    i+=1
    return f"{i:03d}"
def get_page_str(i):
    page_num = get_page_num(i)
    return f"page_{page_num}"
