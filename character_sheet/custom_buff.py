from go_get_it.go_get_it import GoGetDB


class BuffProcessor:
    db = GoGetDB()

    def __init__(self, character_id: str):
        self.character_id = character_id
        self.character = self.db.go_get_one("character", {"id": character_id})
        self.custom_buffs = self.db.go_get_all("custom_buff", {"character_id": character_id})

    def transform_in(self, request_form: dict):
        request_form_copy = dict(request_form)

        if self.custom_buffs is None:
            return request_form_copy

        ability_names = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

        # Pre-fetch current DB base values for all buffable tables
        abilities_db: dict = {}
        skills_db: dict = {}
        for ability_name in ability_names:
            ability = self.db.go_get_one(ability_name, {'character_id': self.character_id}) or {}
            abilities_db[ability_name] = ability
            if ability.get('id'):
                skills = self.db.go_get_one(f"{ability_name}_skills", {f"{ability_name}_id": ability['id']}) or {}
                skills_db[ability_name] = skills

        raw_custom_stats = self.db.go_get_all('custom_stat', {'character_id': self.character_id}) or []
        custom_stats_by_name: dict = {}
        custom_stats_by_id: dict = {}
        for cs in raw_custom_stats:
            name = str(cs.get('name') or '').strip()
            if name:
                custom_stats_by_name.setdefault(name, []).append(cs)
            if cs.get('id'):
                custom_stats_by_id[cs['id']] = cs

        def get_base(table_name: str, stat_name: str, cs_id: str = None) -> int:
            if table_name == 'character':
                return int(self.character.get(stat_name) or 0) if self.character else 0
            elif table_name.endswith('_skills'):
                return int(skills_db.get(table_name[:-7], {}).get(stat_name) or 0)
            elif table_name in ability_names:
                return int(abilities_db.get(table_name, {}).get(stat_name) or 0)
            elif table_name == 'custom_stat' and cs_id:
                return int(custom_stats_by_id.get(cs_id, {}).get('value') or 0)
            return 0

        # First pass: accumulate total buff per form key across all buffs (handles stacking)
        # buff_info[form_key] = {'total_buff': N, 'base': V}
        buff_info: dict = {}

        for buff in self.custom_buffs:
            buff_value = int(buff.get('value') or 0)
            buff_to_table = self.db.go_get_all(
                "custom_buff_to_stat_table",
                {"custom_buff_id": buff['id'], "character_id": self.character_id}
            )
            if buff_to_table is None:
                continue

            for table in buff_to_table:
                stat_table_to_stat = self.db.go_get_all(
                    "stat_table_to_stat",
                    {"character_id": self.character_id, "stat_table_id": table['stat_table_id']}
                )
                table_name = table['stat_table_name']
                if stat_table_to_stat is None:
                    continue

                for stat in stat_table_to_stat:
                    stat_name = stat['stat_name']

                    if table_name == 'custom_stat':
                        for cs in custom_stats_by_name.get(stat_name, []):
                            form_key = f"custom_stat-value-{cs['id']}"
                            if form_key not in buff_info:
                                buff_info[form_key] = {'total_buff': 0, 'base': get_base('custom_stat', stat_name, cs['id'])}
                            buff_info[form_key]['total_buff'] += buff_value
                    else:
                        form_key = f"{table_name}-{stat_name}"
                        if form_key not in buff_info:
                            buff_info[form_key] = {'total_buff': 0, 'base': get_base(table_name, stat_name)}
                        buff_info[form_key]['total_buff'] += buff_value

        # Second pass: compare submitted value against what the user was shown (base + total buff)
        # If unchanged → strip the buff and store the base
        # If changed   → the user typed a new value, treat it as the new base as-is
        for form_key, info in buff_info.items():
            if form_key not in request_form_copy:
                continue
            try:
                submitted = int(request_form_copy[form_key])
            except (TypeError, ValueError):
                continue

            current_base = info['base']
            current_buffed = current_base + info['total_buff']

            if submitted == current_buffed:
                request_form_copy[form_key] = current_base
            else:
                request_form_copy[form_key] = submitted

        return request_form_copy

    def transform_out(self, data: dict):
        custom_buffs = data.get('custom_buffs') or []
        if not custom_buffs:
            return

        abilities_by_name = {
            entry.get('ability_name'): entry
            for entry in data.get('abilities', [])
            if entry.get('ability_name')
        }
        ability_names = set(abilities_by_name.keys())

        custom_stats_by_name: dict = {}
        for stat in data.get('custom_stats', []):
            name = str(stat.get('name') or '').strip()
            if name:
                custom_stats_by_name.setdefault(name, []).append(stat)

        character = data.get('character') or {}

        direct_deltas: dict = {}
        for buff in custom_buffs:
            buff_value = int(buff.get('value') or 0)
            for target in buff.get('targets', []):
                table_name = target.get('stat_table_name', '')
                for stat_name in target.get('stat_names', []):
                    key = (table_name, stat_name)
                    direct_deltas[key] = int(direct_deltas.get(key) or 0) + buff_value

        def add_delta(row: dict, key: str, delta: int):
            if key not in row:
                return
            row[key] = int(row.get(key) or 0) + delta

        for (table_name, stat_name), delta in direct_deltas.items():
            if table_name == 'character':
                add_delta(character, stat_name, delta)
                continue

            if table_name in ability_names:
                if stat_name == 'modifier':
                    continue
                ability = abilities_by_name[table_name].get('ability') or {}
                add_delta(ability, stat_name, delta)
                continue

            if table_name == 'custom_stat':
                for stat in custom_stats_by_name.get(stat_name, []):
                    add_delta(stat, 'value', delta)

        character_proficiency = int(character.get('proficiency') or 0)
        for ability_name, entry in abilities_by_name.items():
            ability = entry.get('ability') or {}
            skills = entry.get('skills') or {}
            skill_list = entry.get('skill_list') or []

            value = int(ability.get('value') or 0)
            modifier = (value - 10) // 2
            ability['modifier'] = modifier

            saving_proficient = int(ability.get('proficient') or 0)
            skills['saving_throw'] = modifier + (character_proficiency if saving_proficient else 0)

            for skill in skill_list:
                skill_proficient = int(skills.get(f"{skill}_proficient") or 0)
                skills[skill] = modifier + (character_proficiency if skill_proficient else 0)

        for (table_name, stat_name), delta in direct_deltas.items():
            if table_name in ability_names and stat_name == 'modifier':
                ability = abilities_by_name[table_name].get('ability') or {}
                add_delta(ability, 'modifier', delta)
                continue

            if table_name.endswith('_skills'):
                ability_name = table_name[:-7]
                entry = abilities_by_name.get(ability_name)
                if not entry:
                    continue
                skills = entry.get('skills') or {}
                add_delta(skills, stat_name, delta)
