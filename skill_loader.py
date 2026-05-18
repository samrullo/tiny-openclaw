import os
import importlib.util


class SkillLoader:
    def __init__(self):
        self.skills = {}

    def load_from_directory(self, skills_dir):
        if not os.path.isdir(skills_dir):
            print(f"No skill directory {skills_dir} found")
            return

        for entry in os.listdir(skills_dir):
            skill_dir = os.path.join(skills_dir, entry)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            handler_py = os.path.join(skill_dir, "handler.py")

            # skip if the skill folder doesn't contain both required files
            if not os.path.isdir(skill_dir):
                continue
            if not os.path.exists(skill_md) or not os.path.exists(handler_py):
                continue

            try:
                # read name and description from SKILL.md
                with open(skill_md) as f:
                    name, description = self._parse_skill_md(f.read())

                # import handler.py at runtime. Tell python where the file is
                spec = importlib.util.spec_from_file_location(
                    f"skill_{entry}", handler_py
                )

                # create an empty module from that spec
                module = importlib.util.module_from_spec(spec)

                # run the file and fill the module with its contents
                spec.loader.exec_module(module)

                # get tools list and execute function from the loaded module
                self.skills[name] = {
                    "name": name,
                    "description": description,
                    "tools": getattr(module, "tools", []),
                    "execute": getattr(module, "execute", None),
                }

                print(f"Skill loaded : {name}")
            except Exception as e:
                print(f"Error while loading a skill {entry} : {e}")

    # helper function to get skill names and descriptions for the system prompt
    def get_active_skills(self):
        return [
            {"name": s["name"], "description": s["description"]}
            for s in self.skills.values()
        ]
    
    # all tool definitions from all skills sent to the LLM
    def get_tools(self):
        tools=[]
        for skill in self.skills.values():
            tools.extend(skill["tools"])
        return tools
    
    # find which skill owns this tool and run it
    async def execute_tool(self, tool_name, tool_input, context):
        for skill in self.skills.values():
            if any(t["name"]==tool_name for t in skill["tools"]):
                if skill["execute"]:
                    return await skill["execute"](tool_name,tool_input,context)
        return {"error":f"Unknown tool {tool_name}"}
    
    # extract name and description from SKILL.md
    def _parse_skill_md(self, content:str):
        name="unknown"
        description=""

        for line in content.split("\n"):
            if line.startswith("name"):
                name = line.split(":",1)[1].strip()
            elif line.startswith("description"):
                description = line.split(":",1)[1].strip()
        return name, description
