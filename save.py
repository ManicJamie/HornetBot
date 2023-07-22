import json, os, shutil, copy, logging

JSON_PATH = "save.json"
data : dict = {} # Do not access directly - use getGuildData or getModuleData instead.
VERSION = 0.1

FULL_TEMPLATE = {
    "version": VERSION,
    "module_templates": {},
    "guild_template": {
        "nick" : "", # NB: automatically set to guild name on addition
        "adminRoles" : [],
        "spoileredPlayers": [],
        "modules" : {} # NB: filled with module_templates on guild instantiation
    },
    "guilds": {}
}

class TemplateEnforcementError(Exception): 
    """Raised when enforcing a module's template"""

def save():
    shutil.copy2(JSON_PATH, JSON_PATH + ".bak")
    # For write-time safety - if we error mid-write then contents of the file won't be completed!

    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)

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

def addModuleTemplate(module_name: str, init_data: dict):
    data["module_templates"][module_name] = copy.deepcopy(init_data)
    save()

def enforceTemplateDict(target: dict, template: dict):
    """Recursive method to enforce a module save template. Verifies only by type. Does not remove extra keys.
    
    Raises `TemplateEnforcementError` if existing key type differs."""
    for k in template.keys():
        if k not in target.keys(): 
            target[k] = template[k]
            continue
        if type(target[k]) != type(template[k]): raise TemplateEnforcementError(k)
        if type(target[k]) == dict: enforceTemplateDict(target[k], template[k])

def getGuildIds() -> list[str]:
    return data["guilds"].keys()

def getModuleData(guild_id, module_name):
    return getGuildData(guild_id)["modules"][module_name]

def getGuildData(guild_id):
    if str(guild_id) not in data["guilds"].keys():
        initGuildData(guild_id)
    return data["guilds"][str(guild_id)]

def initGuildData(guild_id : str, guild_name : str = ""):
    data["guilds"][guild_id] = FULL_TEMPLATE
    data["guilds"][guild_id]["nick"] = guild_name
    data["guilds"][guild_id]["modules"] = copy.deepcopy(data["module_templates"])

def initModule(module_name, init_data=None):
    if init_data is None:
        if module_name not in data["module_templates"]: return # No template added by module, ignore it
        init_data = data["module_templates"][module_name]
    for guild_id in getGuildIds():
        modules = getGuildData(guild_id)["modules"]
        if module_name in modules:
            enforceTemplateDict(modules[module_name], init_data)
        else:
            modules[module_name] = copy.deepcopy(init_data)
    save()