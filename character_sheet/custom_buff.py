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
        """
        Reapplies all active buffs to the data dict before it reaches the frontend.
        Mutates the dict in-place. Uses the 'targets' already built on data['custom_buffs']
        by _get_custom_buffs(), so no extra DB calls are needed.
        """
        custom_buffs = data.get('custom_buffs') or []
        if not custom_buffs:
            return

        # Build lookups so we don't scan lists repeatedly
        abilities_by_name = {
            entry['ability_name']: entry
            for entry in data.get('abilities', [])
        }

        custom_stats_by_name: dict = {}
        for stat in data.get('custom_stats', []):
            name = str(stat.get('name') or '').strip()
            if name:
                custom_stats_by_name.setdefault(name, []).append(stat)

        for buff in custom_buffs:
            buff_value = int(buff.get('value') or 0)
            for target in buff.get('targets', []):
                table_name = target.get('stat_table_name', '')
                for stat_name in target.get('stat_names', []):

                    if table_name == 'character':
                        character = data.get('character') or {}
                        if stat_name in character and character[stat_name] is not None:
                            character[stat_name] = int(character[stat_name]) + buff_value

                    elif table_name.endswith('_skills'):
                        ability_name = table_name[:-7]  # strip '_skills'
                        entry = abilities_by_name.get(ability_name)
                        if entry:
                            skills = entry.get('skills') or {}
                            if stat_name in skills and skills[stat_name] is not None:
                                skills[stat_name] = int(skills[stat_name]) + buff_value

                    elif table_name in abilities_by_name:
                        entry = abilities_by_name[table_name]
                        ability = entry.get('ability') or {}
                        if stat_name in ability and ability[stat_name] is not None:
                            ability[stat_name] = int(ability[stat_name]) + buff_value

                    elif table_name == 'custom_stat':
                        for stat in custom_stats_by_name.get(stat_name, []):
                            if stat.get('value') is not None:
                                stat['value'] = int(stat['value']) + buff_value
