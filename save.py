import json, os, shutil, copy, logging

JSON_PATH = "save.json"
data : dict = {} # Do not access directly - use getGuildData or getModuleData instead.
VERSION = 0.1

FULL_TEMPLATE = {
    "version": VERSION,
    "module_templates": {},
    "global_module_templates": {},
    "guild_template": {
        "nick" : "", # NB: automatically set to guild name on addition
        "adminRoles" : [],
        "spoileredPlayers": [],
        "logChannel": None,
        "modules" : {} # NB: filled with module_templates on guild instantiation
    },
    "modules": {}, # NB: filled with global_module_templates on module instantiation
    "guilds": {}
}

class TemplateEnforcementError(Exception): 
    """Raised when enforcing a module's template"""

def save():
    shutil.copy2(JSON_PATH, JSON_PATH + ".bak")
    # For write-time safety - if we error mid-write then contents of the file won't be completed!

    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)

def add_module_template(module_name: str, init_data: dict):
    data["module_templates"][module_name] = copy.deepcopy(init_data)
    save()

def add_global_module_template(module_name: str, init_data: dict):
    data["global_module_templates"][module_name] = copy.deepcopy(init_data)
    save()

def enforce_template_dict(target: dict, template: dict):
    """Recursive method to enforce a module save template. Verifies only by type. Does not remove extra keys.

    Raises `TemplateEnforcementError` if existing key type differs."""
    for k, template_value in template.items():
        target_value = target.get(k, None)
        if target_value is None:
            target[k] = template_value
            continue
        if type(target_value) != type(template_value): raise TemplateEnforcementError(k)
        if isinstance(target_value, dict): enforce_template_dict(target_value, template_value)

def get_guild_ids() -> list[str]:
    return data["guilds"].keys()

def get_module_data(guild_id, module_name):
    return get_guild_data(guild_id)["modules"][module_name]

def get_global_module(module_name):
    return data["global_module_templates"][module_name]

def get_guild_data(guild_id):
    if str(guild_id) not in data["guilds"]:
        logging.warn("Guild not found: instantiating")
        init_guild_data(str(guild_id))
    return data["guilds"][str(guild_id)]

def init_guild_data(guild_id : str, guild_name : str = ""):
    data["guilds"][guild_id] = data["guild_template"]
    data["guilds"][guild_id]["nick"] = guild_name
    data["guilds"][guild_id]["modules"] = copy.deepcopy(data["module_templates"])
    save()

def init_module(module_name, init_data=None):
    if init_data is None:
        if module_name not in data["module_templates"]: 
            if module_name in data["global_module_templates"]:
                init_global_module(module_name, init_data)
            else:
                return # No template added by module, ignore it
        init_data = data["module_templates"][module_name]
    for guild_id in get_guild_ids():
        modules = get_guild_data(guild_id)["modules"]
        if module_name in modules:
            enforce_template_dict(modules[module_name], init_data)
        else:
            modules[module_name] = copy.deepcopy(init_data)
    save()

def init_global_module(module_name, init_data=None):
    if init_data is None:
        if module_name not in data["global_module_templates"]: return # No template added by module, ignore it
        init_data = data["global_module_templates"][module_name]
    if module_name in data["modules"]:
        enforce_template_dict(data["modules"][module_name], init_data)
    else:
        data["modules"][module_name] = copy.deepcopy(init_data)
    save()

if not os.path.exists(JSON_PATH):
    data = FULL_TEMPLATE
    save()
else:
    with open(JSON_PATH) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            logging.warn("Could not deserialise save.json - loading backup")
            with open(JSON_PATH + ".bak") as f2:
                data = json.load(f2)
        if VERSION > data["version"]:
            logging.error(f"Save json is out of date! Json ver: {data['version']} < Save ver: {VERSION}")
            exit(11)
    
    enforce_template_dict(data, FULL_TEMPLATE)
    save()
    pass