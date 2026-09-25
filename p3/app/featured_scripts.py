import json
import os
import random

from .gtk_common import Gdk, GLib
from . import parser, popularity, category_affinity, installed_packages, _catalog_rs
from .revert_helper import _get_executed_script_names


class FeaturedCtl:
    FEATURED_REFRESH_MIN_SECONDS = 8
    FEATURED_REFRESH_MAX_SECONDS = 15
    FEATURED_REFRESH_MIN_ITEMS = 10
    FEATURED_REFRESH_MAX_ITEMS = 25
    FEATURED_MAX_ROWS = 10
    FEATURED_RESIZE_DEBOUNCE_MS = 150
    FEATURED_SWAP_ANIMATION_MS = 180

    SENSE_HISTORY_LIMIT = 2
    SENSE_PERSONALIZED_PERCENT = 80

    def _invalidate_featured_eligibility_cache(self):
        """Discard Featured eligibility after installed/registry state changes."""
        self._featured_eligibility_cache = None

    @staticmethod
    def _sense_file_path():
        return os.path.expanduser("~/.cache/linuxtoys/sense")

    def _load_featured_sense(self):
        """Load the previous session's most recently entered categories."""
        self._featured_sensed_categories = []
        try:
            with open(self._sense_file_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError, TypeError):
            return

        if not isinstance(data, list):
            return

        seen = set()
        for value in data:
            value = str(value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            self._featured_sensed_categories.append(value)
            if len(self._featured_sensed_categories) >= self.SENSE_HISTORY_LIMIT:
                break

    def _record_featured_category(self, category_info):
        """Remember a category in RAM; persistence happens only during shutdown."""
        if not category_info or category_info.get("is_script"):
            return
        category_path = str(category_info.get("path", "") or "").strip()
        if not category_path:
            return
        category_path = os.path.abspath(category_path)

        history = list(getattr(self, "_featured_sensed_categories", ()))
        history = [path for path in history if path != category_path]
        history.insert(0, category_path)
        self._featured_sensed_categories = history[: self.SENSE_HISTORY_LIMIT]

    def _save_featured_sense(self):
        """Persist category sense once, when LinuxToys is closing."""
        history = list(getattr(self, "_featured_sensed_categories", ()))[: self.SENSE_HISTORY_LIMIT]
        path = self._sense_file_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(history, handle, ensure_ascii=False)
                handle.write("\n")
        except OSError as error:
            print(f"Warning: Could not save Featured sense data: {error}")

    def _personalized_featured_category_paths(self):
        """Return recent + strongest installed categories, without materializing them."""
        category_cache = getattr(self, "category_cache", None)
        if category_cache is None:
            return []

        paths = []
        seen = set()

        # Recency contributes at most the last two categories entered.
        for category_path in getattr(self, "_featured_sensed_categories", ()):
            category_path = os.path.abspath(str(category_path or "").strip())
            if not category_path or category_path in seen:
                continue
            seen.add(category_path)
            paths.append(category_path)
            if len(paths) >= self.SENSE_HISTORY_LIMIT:
                break

        # Count installed LinuxToys entries directly from the structural cache.
        # Crucially, do not call get_scripts_for_category(): that would lazily
        # materialize every AppStream entry in every category just to count the
        # handful that are installed.
        installed_by_category = {}
        try:
            categories = category_cache.get_categories()
        except Exception:
            categories = ()

        category_paths = []
        for category in categories or ():
            if category.get("is_script"):
                continue
            category_path = str(category.get("path", "") or "").strip()
            if not category_path:
                continue
            category_path = os.path.abspath(category_path)
            category_paths.append(category_path)

            structural = category_cache.scripts_by_category.get(category_path, ())
            count = sum(
                1
                for script in structural
                if script.get("is_script", False)
                and not script.get("is_create_script", False)
                and self._is_script_removable(script)
            )
            if count:
                installed_by_category[category_path] = count

        # AppStream already has package/name indexes in Rust. Ask it only for the
        # entries matching the installed snapshot, then count those few entries by
        # category in Python. This preserves Registry-managed AppStream installs too.
        try:
            snapshot = installed_packages.snapshot()
            if snapshot.get("loaded"):
                appstream_installed = parser.get_installed_appstream_entries(
                    snapshot.get("native", ()),
                    snapshot.get("flatpak", {}).keys(),
                    executed_names=_get_executed_script_names(),
                    translations=self.translations,
                )
            else:
                appstream_installed = ()
        except Exception:
            appstream_installed = ()

        scripts_root = os.path.abspath(parser.SCRIPTS_DIR)
        valid_paths = set(category_paths)
        for script in appstream_installed or ():
            category = str(script.get("category", "") or "").strip().strip("/")
            if not category:
                continue
            category_path = os.path.abspath(os.path.join(scripts_root, *category.split("/")))
            if category_path not in valid_paths:
                continue
            installed_by_category[category_path] = installed_by_category.get(category_path, 0) + 1

        installed_counts = [
            (count, category_path)
            for category_path, count in installed_by_category.items()
            if count > 0
        ]

        # Stable path tie-break makes equal-count ordering deterministic. Categories
        # already supplied by recency simply consume one of the possible categories;
        # do not backfill with a third/fourth installed category when they coincide.
        installed_counts.sort(key=lambda item: (-item[0], item[1]))
        for _count, category_path in installed_counts[:2]:
            if category_path in seen:
                continue
            seen.add(category_path)
            paths.append(category_path)

        return paths

    def _sensed_featured_keys(self):
        """Return eligible identities from the main menu's personalized categories."""
        category_cache = getattr(self, "category_cache", None)
        if category_cache is None:
            return set()

        keys = set()
        for category_path in self._personalized_featured_category_paths():
            try:
                scripts = category_cache.get_scripts_for_category(category_path)
            except Exception:
                continue
            for script in scripts or ():
                if script.get("is_script", False) and not script.get("is_create_script", False):
                    keys.add(self._featured_script_key(script))
        return keys

    def _collect_all_scripts(self):
        """Collect direct top-level scripts, preferring already parsed cache data."""
        all_scripts = []
        seen = set()

        def add_scripts(scripts):
            for script in scripts:
                if (
                    not script.get("is_script", False)
                    or script.get("is_create_script", False)
                ):
                    continue
                key = script.get("path") or (
                    script.get("name", ""),
                    script.get("repo", ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                all_scripts.append(script)

        try:
            category_cache = getattr(self, "category_cache", None)
            if category_cache is not None and category_cache.scripts_by_category:
                categories = category_cache.get_categories()
                for category in categories:
                    if category.get("is_script"):
                        continue
                    category_path = category.get("path", "")
                    if category_path:
                        # Featured startup already owns the structural category
                        # snapshot. Do not trigger lazy AppStream materialization merely
                        # to discard those entries again below.
                        add_scripts(
                            category_cache.scripts_by_category.get(
                                os.path.abspath(category_path), ()
                            )
                        )
                add_scripts(parser.get_appstream_featured_descriptors(self.translations))
                return all_scripts

            # Compatibility fallback for callers that do not own a CategoryCache.
            categories = parser.get_categories(self.translations)
            for category in categories:
                if category.get("is_script"):
                    continue
                category_path = category.get("path", "")
                if not category_path:
                    continue
                try:
                    add_scripts(
                        script for script in parser.get_scripts_for_category(
                            category_path,
                            self.translations,
                        )
                        if not script.get("is_appstream_entry", False)
                    )
                except Exception:
                    continue
            add_scripts(parser.get_appstream_featured_descriptors(self.translations))

        except Exception as error:
            print(f"Error collecting all scripts: {error}")

        return all_scripts

    @staticmethod
    def _preferred_height(widget):
        """Return a widget's natural preferred height."""
        if widget is None:
            return 0

        try:
            _minimum, natural = widget.get_preferred_height()
            return natural
        except (AttributeError, TypeError):
            return widget.get_allocated_height()

    @staticmethod
    def _preferred_width(widget):
        """Return a widget's natural preferred width."""
        if widget is None:
            return 0

        try:
            _minimum, natural = widget.get_preferred_width()
            return natural
        except (AttributeError, TypeError):
            return widget.get_allocated_width()

    def _get_featured_card_size(self):
        """Return the stable representative Featured card measurement."""
        cached = getattr(self, "_featured_card_size_cache", None)
        if cached is not None:
            return cached

        sample = None
        temporary_sample = False

        category_children = self.categories_flowbox.get_children()
        if category_children:
            sample = category_children[0].get_child()

        if sample is None and self.all_scripts:
            sample = self.create_item_widget(self.all_scripts[0])
            temporary_sample = True

        card_width = self._preferred_width(sample)
        card_height = self._preferred_height(sample)

        if temporary_sample:
            sample.destroy()

        # Safe fallbacks for the first allocation cycle. Cache only a real
        # measurement; fallback geometry is intentionally retried later.
        result = (max(1, card_width or 120), max(1, card_height or 64))
        if card_width > 0 and card_height > 0:
            self._featured_card_size_cache = result
        return result

    def _invalidate_featured_measurements(self):
        """Invalidate stable measurements after content/theme/language rebuilds."""
        self._featured_card_size_cache = None

    def _calculate_featured_columns(self):
        """Mirror the main menu's *actual* currently allocated column count."""
        category_children = self.categories_flowbox.get_children()
        columns = 0

        # FlowBox does not expose its current effective column count directly.
        # Once allocated, however, every child in the same row has the same Y
        # coordinate. Count the fullest allocated row so this follows GTK's real
        # layout decision instead of trying to reproduce it from preferred widths.
        row_counts = {}
        for child in category_children:
            allocation = child.get_allocation()
            if allocation.width <= 1 or allocation.height <= 1:
                continue
            row_counts[allocation.y] = row_counts.get(allocation.y, 0) + 1

        if row_counts:
            columns = max(row_counts.values())

        # During the first allocation cycle there may not be usable child geometry
        # yet. Be conservative; the size-allocate callback will recalculate this as
        # soon as GTK has laid out the main menu. This avoids ever over-populating
        # the featured section during startup.
        if columns <= 0:
            columns = 1

        main_max_columns = self.categories_flowbox.get_max_children_per_line()
        if main_max_columns > 0:
            columns = min(columns, main_max_columns)

        columns = max(1, int(columns))

        return columns

    def calculate_featured_capacity(
        self,
        viewport_height,
        used_height,
        *,
        fixed_height=0,
        row_spacing=None,
        bottom_padding=0,
        max_rows=None,
    ):
        """
        Calculate Featured rows/columns from the same geometry used by the main menu.

        ``used_height`` is the bottom edge already occupied by normal content in
        the viewport. Callers supply only their context-specific fixed section
        overhead; card size and effective columns remain shared with the main menu.
        """
        viewport_height = int(viewport_height or 0)
        used_height = int(used_height or 0)
        fixed_height = max(0, int(fixed_height or 0))
        bottom_padding = max(0, int(bottom_padding or 0))

        if viewport_height <= 1 or used_height < 0:
            return None

        _card_width, card_height = self._get_featured_card_size()
        if row_spacing is None:
            row_spacing = self.random_scripts_flowbox.get_row_spacing()
        row_spacing = max(0, int(row_spacing or 0))

        available_rows_height = (
            viewport_height - used_height - fixed_height - bottom_padding
        )
        if available_rows_height < card_height:
            return None

        rows = 1 + (
            available_rows_height - card_height
        ) // (card_height + row_spacing)

        if max_rows is not None:
            rows = min(int(max_rows), int(rows))
        rows = max(0, int(rows))
        if rows <= 0:
            return None

        columns = self._calculate_featured_columns()
        if columns <= 0:
            return None

        return {
            "rows": rows,
            "columns": columns,
            "card_height": card_height,
            "row_spacing": row_spacing,
            "available_rows_height": available_rows_height,
        }

    @staticmethod
    def _calculate_featured_large_count(rows, columns, eligible_count):
        """Return the large-card allowance shared by main-menu and app-page Featured."""
        rows = max(0, int(rows or 0))
        columns = max(0, int(columns or 0))
        eligible_count = max(0, int(eligible_count or 0))
        if rows >= 9:
            max_large_cards = max(3, columns)
        else:
            max_large_cards = min(3, rows // 3)
        if rows > 6:
            max_large_cards += columns // 2
        return min(max_large_cards, eligible_count)

    def _calculate_random_scripts_count(self):
        """Calculate Featured geometry and the number of actual app cards shown."""
        if (
            not self.all_scripts
            or self.current_category_info is not None
            or self.main_stack.get_visible_child_name() != "categories"
        ):
            self._featured_layout_metrics = None
            return 0

        viewport_height = self.categories_view.get_allocated_height()
        categories_height = self.categories_flowbox.get_allocated_height()

        if viewport_height <= 1 or categories_height <= 1:
            self._featured_layout_metrics = None
            return 0

        container = self.featured_scripts_container
        vertical_margins = (
            container.get_margin_top() + container.get_margin_bottom()
        )

        separator = None
        children = container.get_children()
        if children:
            separator = children[0]

        separator_height = self._preferred_height(separator)
        label_height = self._preferred_height(self.random_scripts_label)
        section_spacing = container.get_spacing() * 2
        fixed_featured_height = (
            vertical_margins
            + separator_height
            + label_height
            + section_spacing
        )
        capacity = self.calculate_featured_capacity(
            viewport_height,
            categories_height,
            fixed_height=fixed_featured_height,
            row_spacing=self.random_scripts_flowbox.get_row_spacing(),
            max_rows=self.FEATURED_MAX_ROWS,
        )
        if capacity is None:
            self._featured_layout_metrics = None
            return 0

        rows = capacity["rows"]
        columns = capacity["columns"]
        card_height = capacity["card_height"]
        row_spacing = capacity["row_spacing"]

        eligible_count = len(self._eligible_featured_scripts())
        if eligible_count <= 0:
            self._featured_layout_metrics = None
            return 0

        # A large card occupies three normal grid cells, so every one reduces the
        # number of distinct apps that fit by two while preserving exactly the
        # same overall Featured height and column count. The allowance itself is
        # shared with app-page Featured.
        large_count = self._calculate_featured_large_count(
            rows, columns, eligible_count
        )
        slot_count = rows * columns
        item_capacity = max(0, slot_count - (2 * large_count))
        item_count = min(eligible_count, item_capacity)
        large_count = min(large_count, item_count)

        # If a very small eligible pool forced large_count down, reclaim the slots
        # that no longer need to be reserved by a three-row card.
        item_capacity = max(0, slot_count - (2 * large_count))
        item_count = min(eligible_count, item_capacity)

        self._featured_layout_metrics = {
            "rows": rows,
            "columns": columns,
            "card_height": card_height,
            "row_spacing": row_spacing,
            "large_count": large_count,
            "item_count": item_count,
        }
        return item_count

    @staticmethod
    def _featured_script_key(script):
        """Return a stable identity for Featured history/exclusion checks."""
        return script.get("path") or (
            script.get("name", ""),
            script.get("repo", ""),
        )

    @staticmethod
    def _featured_rating_weight(script):
        """Return the Featured selection weight for an eligible candidate.

        LinuxToys-curated entries keep the historical baseline weight. AppStream
        entries require at least 3.5 stars (70 on the ODRS 0-100 scale); their weight
        then rises linearly from 1.0 at 70 to 2.0 at 90 (4.5 stars) and remains
        capped there.
        """
        if not script.get("is_appstream_entry", False):
            return 1.0

        try:
            rating = float(script.get("review_rating"))
        except (TypeError, ValueError):
            return 0.0

        if rating < 70.0:
            return 0.0
        return min(2.0, 1.0 + ((rating - 70.0) / 20.0))

    @staticmethod
    def _featured_popularity_weight(script):
        """Return a bounded 1..2 popularity multiplier for Featured sampling."""
        try:
            score = popularity.score_for_item(script)
        except Exception:
            score = 0
        return 1.0 + (max(0, min(popularity.SCORE_MAX, int(score))) / popularity.SCORE_MAX)

    @classmethod
    def _weighted_featured_sample(cls, candidates, count, extra_weight=None):
        """Sample without replacement with one weight pass and one Rust call."""
        pool = list(candidates)
        count = min(max(0, int(count or 0)), len(pool))
        if count <= 0:
            return []

        # These weights are invariant during this selection. Compute each exactly
        # once instead of recomputing the whole shrinking pool for every draw.
        weights = []
        for script in pool:
            weight = (
                cls._featured_rating_weight(script)
                * cls._featured_popularity_weight(script)
            )
            if extra_weight is not None:
                try:
                    weight *= max(0.0, float(extra_weight(script)))
                except (TypeError, ValueError):
                    pass
            weights.append(weight)

        if not any(weight > 0.0 for weight in weights):
            return []

        # Keep Python's RNG as the entropy source; Rust only executes the weighted
        # sequential removals. This avoids adding an RNG dependency to the extension.
        draws = [random.random() for _ in range(count)]
        indices = _catalog_rs.featured_weighted_sample(weights, draws, count)
        return [pool[index] for index in indices]

    def _eligible_featured_scripts(self):
        """Return Featured eligibility from one installed/registry-state snapshot."""
        cached = getattr(self, "_featured_eligibility_cache", None)
        if cached is not None:
            cached_source, cached_items = cached
            if cached_source is self.all_scripts:
                return cached_items

        # Registry and installed-package state are shared by the entire candidate
        # pool. Read each once instead of making every AppStream descriptor repeat
        # the same registry parse / installed-state lookup.
        try:
            executed_names = _get_executed_script_names()
        except Exception:
            executed_names = set()

        try:
            installed_snapshot = installed_packages.snapshot()
        except Exception:
            installed_snapshot = {
                "manager": None,
                "native": set(),
                "flatpak": {},
                "loaded": False,
            }

        native = installed_snapshot.get("native", set())
        flatpak = installed_snapshot.get("flatpak", {})

        def appstream_is_removable(script):
            if script.get("name") in executed_names:
                return True

            source = str(script.get("appstream_source", "") or "").strip()
            value = script.get("package-name") or ()

            if source == "flatpak":
                # Runtime descriptors retain the package-name list. AppStream's
                # Flatpak representation normally has one application ID, but
                # accept all values so this remains robust to overlays.
                packages = [value] if isinstance(value, str) else list(value)
                if not packages:
                    packages = [script.get("appstream_id", "")]
                return any(
                    str(package or "").strip().casefold() in flatpak
                    for package in packages
                    if str(package or "").strip()
                )

            if source == "native":
                packages = [value] if isinstance(value, str) else list(value)
                return any(str(package) in native for package in packages)

            return False

        eligible = []
        for script in self.all_scripts:
            if script.get("is_appstream_entry"):
                removable = appstream_is_removable(script)
            else:
                # Structural/repository entries are already represented in
                # ScriptCache's removable cache, so this is normally a dict lookup.
                removable = self._is_script_removable(script)

            if not removable and self._featured_rating_weight(script) > 0:
                eligible.append(script)

        self._featured_eligibility_cache = (self.all_scripts, eligible)
        return eligible

    @staticmethod
    def _featured_history_limit(count):
        """How many previous Featured sets must remain excluded."""
        if count < 10:
            return 3
        if count < 20:
            return 2
        return 1

    @staticmethod
    def _is_linuxtoys_curated_featured(script):
        """Return whether a Featured candidate comes from LinuxToys itself."""
        return not script.get("is_appstream_entry", False)

    def _materialize_featured_selection(self, selected):
        """Replace selected AppStream descriptors with their full Rust payloads."""
        selected = list(selected or ())
        indices = [
            script.get("_appstream_featured_index")
            for script in selected
            if script.get("_appstream_featured_index") is not None
        ]
        if not indices:
            return selected

        try:
            full_entries = parser.materialize_appstream_featured_entries(
                indices, self.translations
            )
        except Exception as error:
            print(f"Error materializing selected AppStream Featured entries: {error}")
            full_entries = ()

        full_by_key = {
            self._featured_script_key(script): script
            for script in full_entries or ()
        }
        result = []
        for script in selected:
            if script.get("_appstream_featured_index") is None:
                result.append(script)
                continue
            full = full_by_key.get(self._featured_script_key(script))
            if full is not None:
                result.append(full)
        return result

    def _select_random_scripts(self, count):
        """Select Featured cards, biasing 80% toward personalized categories."""
        if not self.all_scripts or count <= 0:
            return []

        eligible = self._eligible_featured_scripts()
        if not eligible:
            return []

        count = min(count, len(eligible))
        history = list(getattr(self, "_featured_history", ()))
        history_limit = self._featured_history_limit(count)
        history = history[-history_limit:]

        # Preserve the existing no-repeat window, relaxing only as much as needed
        # to keep the current Featured layout full.
        while True:
            excluded = set().union(*history) if history else set()
            candidates = [
                script for script in eligible
                if self._featured_script_key(script) not in excluded
            ]
            if len(candidates) >= count or not history:
                break
            history.pop(0)

        self._featured_history = history

        sensed_categories = self._personalized_featured_category_paths()

        def sensed_affinity(script):
            return category_affinity.affinity_from_sources(
                sensed_categories, script.get("category")
            )

        # The personalized share is no longer a binary exact-category pool. Myket's
        # offline co-installation prior expands it to statistically related areas.
        # Its multiplier tops out at 1.5x, deliberately below both the 2x review
        # and 2x popularity multipliers used by the base Featured sampler.
        sensed_candidates = [script for script in candidates if sensed_affinity(script) > 0.0]
        sensed_target = (count * self.SENSE_PERSONALIZED_PERCENT) // 100
        sensed_count = min(sensed_target, len(sensed_candidates), count)
        selected = self._weighted_featured_sample(
            sensed_candidates, sensed_count,
            extra_weight=lambda script: 1.0 + (0.50 * sensed_affinity(script)),
        )
        sensed_keys = {self._featured_script_key(script) for script in sensed_candidates}
        selected_keys = {self._featured_script_key(script) for script in selected}

        # The remaining share keeps the previous global random discovery behavior.
        remaining_candidates = [
            script for script in candidates
            if self._featured_script_key(script) not in selected_keys
        ]
        remaining_count = count - len(selected)
        if remaining_count > 0:
            selected.extend(
                self._weighted_featured_sample(
                    remaining_candidates,
                    min(remaining_count, len(remaining_candidates)),
                )
            )

        # Preserve the existing LinuxToys-curated minimum. Prefer satisfying it by
        # replacing globally-random cards so the personalized 80% remains intact
        # whenever the candidate pool allows it.
        curated_required = min(
            max(1, count // 5),
            sum(self._is_linuxtoys_curated_featured(script) for script in candidates),
            count,
        )
        curated_have = sum(self._is_linuxtoys_curated_featured(script) for script in selected)
        if curated_have < curated_required:
            selected_keys = {self._featured_script_key(script) for script in selected}
            curated_pool = [
                script for script in candidates
                if self._is_linuxtoys_curated_featured(script)
                and self._featured_script_key(script) not in selected_keys
            ]
            random.shuffle(curated_pool)
            replacements_needed = min(curated_required - curated_have, len(curated_pool))

            replaceable = [
                index for index, script in enumerate(selected)
                if not self._is_linuxtoys_curated_featured(script)
                and self._featured_script_key(script) not in sensed_keys
            ]
            replaceable += [
                index for index, script in enumerate(selected)
                if not self._is_linuxtoys_curated_featured(script)
                and self._featured_script_key(script) in sensed_keys
                and index not in replaceable
            ]
            for index, replacement in zip(replaceable, curated_pool[:replacements_needed]):
                selected[index] = replacement

        random.shuffle(selected)
        return self._materialize_featured_selection(selected)

    def select_featured_scripts_for_app_page(
        self, count, exclude_keys=(), category=None
    ):
        """Select app-page Featured with Myket affinity as the master criterion.

        The ordinary Featured eligibility gate still applies (including the 3.5-star
        ODRS minimum for AppStream entries). Among eligible candidates, category
        affinity to the current app is authoritative; reviews and popularity break
        ties/near-equivalent relationships, followed by stable session randomness.
        """
        if count <= 0:
            return []

        excluded = set(exclude_keys or ())
        category = str(category or "").strip().replace("\\", "/").strip("/")
        eligible = [
            script
            for script in self._eligible_featured_scripts()
            if self._featured_script_key(script) not in excluded
        ]
        if not eligible:
            return []

        count = min(int(count), len(eligible))

        def recommendation_key(script):
            affinity = category_affinity.affinity(category, script.get("category"))
            try:
                review = float(script.get("review_subscore"))
            except (TypeError, ValueError):
                try:
                    review = float(script.get("review_rating")) * 10.0
                except (TypeError, ValueError):
                    review = 0.0
            try:
                pop = popularity.score_for_item(script)
            except Exception:
                pop = 0
            # Affinity is intentionally first: app-page Featured is a related-app
            # surface, not another popularity chart. The minimum review threshold
            # has already been enforced by _eligible_featured_scripts().
            return (-affinity, -review, -pop, random.random())

        eligible.sort(key=recommendation_key)
        return self._materialize_featured_selection(eligible[:count])


    def _choose_featured_large_positions(self, rows, columns, count):
        """Pick moved large spans while minimizing ordinary-card replacement."""
        if count <= 0 or rows < 3 or columns <= 0:
            self._featured_large_positions = set()
            return []

        previous = set(getattr(self, "_featured_large_positions", set()))
        all_positions = [
            (column, row)
            for column in range(columns)
            for row in range(rows - 2)
        ]

        def find_layout(candidates):
            candidates = list(candidates)
            random.shuffle(candidates)

            def overlaps(position, chosen):
                column, row = position
                return any(
                    column == other_column
                    and not (row + 2 < other_row or other_row + 2 < row)
                    for other_column, other_row in chosen
                )

            def search(index, chosen):
                if len(chosen) == count:
                    return list(chosen)
                if len(candidates) - index < count - len(chosen):
                    return None
                for candidate_index in range(index, len(candidates)):
                    candidate = candidates[candidate_index]
                    if overlaps(candidate, chosen):
                        continue
                    result = search(candidate_index + 1, chosen + [candidate])
                    if result is not None:
                        return result
                return None

            return search(0, [])

        # Preserve the existing rule that large cards should move. Generate several
        # valid moved layouts, then choose the one that changes the fewest occupied
        # cells. This directly maximizes the number of ordinary cards we can rebind.
        fresh_positions = [pos for pos in all_positions if pos not in previous]
        candidates = []
        for _ in range(32):
            layout = find_layout(fresh_positions)
            if layout is not None:
                candidates.append(layout)

        if not candidates:
            # Geometry can make a completely fresh set impossible.
            for _ in range(32):
                layout = find_layout(all_positions)
                if layout is not None:
                    candidates.append(layout)

        if not candidates:
            self._featured_large_positions = set()
            return []

        previous_cells = set()
        for position in previous:
            previous_cells.update(self._featured_occupied_cells(position))

        def changed_cells(layout):
            new_cells = set()
            for position in layout:
                new_cells.update(self._featured_occupied_cells(position))
            return len(previous_cells.symmetric_difference(new_cells))

        best_cost = min(changed_cells(layout) for layout in candidates)
        best = [layout for layout in candidates if changed_cells(layout) == best_cost]
        chosen = random.choice(best)
        self._featured_large_positions = set(chosen)
        return chosen

    @staticmethod
    def _featured_occupied_cells(position):
        column, row = position
        return {(column, row + offset) for offset in range(3)}

    def _clear_random_scripts(self):
        """Remove every currently displayed featured card."""
        for child in self.random_scripts_flowbox.get_children():
            child.destroy()

    def _hide_featured_section(self, discard=False):
        """Hide Featured Scripts without losing its current state by default."""
        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None

        self.random_scripts_revealer.set_reveal_child(False)
        self.featured_scripts_revealer.set_reveal_child(False)

        if discard:
            self._clear_random_scripts()
            self._featured_last_count = 0
            self._featured_last_layout = None
            self._featured_history = []
            self._featured_large_positions = set()

    def _invalidate_featured_scripts(self):
        """Discard Featured state when its backing script data becomes stale."""
        self._stop_random_scripts_refresh_timer()
        self._hide_featured_section(discard=True)

    def _reveal_initial_featured_layout(self):
        """Reveal the first Featured set after GTK has negotiated its final size."""
        if (
            not self.all_scripts
            or self.current_category_info is not None
            or self.main_stack.get_visible_child_name() != "categories"
        ):
            return False

        self.featured_scripts_revealer.set_reveal_child(True)
        self.random_scripts_revealer.set_reveal_child(True)
        return False

    def _populate_random_scripts(self, scripts, count, layout):
        """
        Replace Featured content.

        Geometry changes deliberately use the original full redraw. When geometry
        is unchanged, ordinary cards whose cells remain ordinary are rebound in
        place; only large cards and cells whose role changes are rebuilt.
        """
        self._featured_swap_timer = None
        self._featured_swap_required_by_layout = False

        on_categories_view = (
            self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
        )
        if not self.all_scripts or not on_categories_view or count <= 0:
            return False

        rows = int(layout.get("rows", 0))
        columns = int(layout.get("columns", 0))
        large_count = min(int(layout.get("large_count", 0)), len(scripts))
        card_height = int(layout.get("card_height", 52))
        row_spacing = int(layout.get("row_spacing", 12))
        if rows <= 0 or columns <= 0:
            return False

        new_signature = (rows, columns, large_count, count)
        previous_signature = getattr(self, "_featured_last_layout", None)
        existing_children = list(self.random_scripts_flowbox.get_children())
        same_geometry = bool(existing_children) and previous_signature == new_signature

        # A resize/maximize/restore that changes rows, columns, large allowance or
        # item count intentionally falls back to the proven original behavior.
        if not same_geometry:
            self._clear_random_scripts()
            existing_children = []
            # A new geometry has no meaningful large-card placement to preserve.
            self._featured_large_positions = set()

        previous_large_positions = set(
            getattr(self, "_featured_large_positions", set())
        )
        large_positions = self._choose_featured_large_positions(
            rows, columns, large_count
        )
        large_count = min(large_count, len(large_positions))

        localized_scripts = [
            script for script in scripts
            if script.get("description_localized", False)
        ]
        other_scripts = [
            script for script in scripts
            if not script.get("description_localized", False)
        ]
        random.shuffle(localized_scripts)
        random.shuffle(other_scripts)

        if len(localized_scripts) >= large_count:
            large_scripts = localized_scripts[:large_count]
            normal_scripts = localized_scripts[large_count:] + other_scripts
        else:
            needed = large_count - len(localized_scripts)
            large_scripts = localized_scripts + other_scripts[:needed]
            normal_scripts = other_scripts[needed:]

        random.shuffle(large_scripts)
        random.shuffle(normal_scripts)
        random.shuffle(large_positions)

        occupied = set()
        for position in large_positions:
            occupied.update(self._featured_occupied_cells(position))

        previous_occupied = set()
        for position in previous_large_positions:
            previous_occupied.update(self._featured_occupied_cells(position))

        large_height = (3 * card_height) + (2 * row_spacing)

        def prepare_widget(script_info, *, large=False):
            widget = self.create_item_widget(
                script_info,
                featured_large=large,
                featured_height=large_height if large else 0,
            )
            widget._featured_grid_large = large
            description = script_info.get("description", "")
            widget.set_tooltip_text(description or None)
            widget.set_can_focus(True)
            widget.connect("key-press-event", self._on_featured_card_key_press)
            widget.add_events(
                Gdk.EventMask.ENTER_NOTIFY_MASK
                | Gdk.EventMask.LEAVE_NOTIFY_MASK
            )
            widget.connect("enter-notify-event", self._on_featured_card_enter)
            widget.connect("leave-notify-event", self._on_featured_card_leave)
            return widget

        reusable_normals = {}
        if same_geometry:
            # Read positions from Gtk.Grid itself. Stable ordinary cells remain
            # parented throughout the swap; large cards and role-changing cells do not.
            for widget in existing_children:
                left = self.random_scripts_flowbox.child_get_property(widget, "left-attach")
                top = self.random_scripts_flowbox.child_get_property(widget, "top-attach")
                width = self.random_scripts_flowbox.child_get_property(widget, "width")
                height = self.random_scripts_flowbox.child_get_property(widget, "height")
                position = (int(left), int(top))

                if int(width) == 1 and int(height) == 1 and position not in occupied:
                    reusable_normals[position] = widget
                else:
                    widget.destroy()

        # Large cards are intentionally cheap structural churn. We do not try to
        # preserve/reparent them; the placement algorithm instead minimizes how many
        # ordinary cells have to be sacrificed when the large spans move.
        for script_info, position in zip(large_scripts, large_positions):
            column, row = position
            widget = prepare_widget(script_info, large=True)
            self.random_scripts_flowbox.attach(widget, column, row, 1, 3)

        free_cells = [
            (column, row)
            for row in range(rows)
            for column in range(columns)
            if (column, row) not in occupied
        ]

        for script_info, position in zip(normal_scripts, free_cells):
            widget = reusable_normals.pop(position, None)
            if widget is not None:
                self.update_featured_normal_widget(widget, script_info)
            else:
                widget = prepare_widget(script_info, large=False)
                column, row = position
                self.random_scripts_flowbox.attach(widget, column, row, 1, 1)

        # Defensive cleanup if selection/capacity ever leaves an old normal card
        # without a corresponding new item.
        for widget in reusable_normals.values():
            widget.destroy()

        self._featured_last_count = count
        self._featured_last_layout = new_signature

        displayed_keys = {
            self._featured_script_key(script_info)
            for script_info in scripts
        }
        history_limit = self._featured_history_limit(count)
        history = list(getattr(self, "_featured_history", ()))
        history.append(displayed_keys)
        self._featured_history = history[-history_limit:]

        # The surrounding Featured hierarchy was already shown during window
        # startup. Only cards attached after that point start hidden, so limit the
        # recursive show traversal to the grid instead of the whole revealer tree.
        self.random_scripts_flowbox.show_all()

        # On the very first Featured draw GTK may still be propagating the new
        # Gtk.Grid requisition through the nested revealer/container hierarchy.
        # This is especially easy to hit on the fast startup path where the
        # AppStream runtime pickle is already available. Revealing immediately
        # can therefore expose one transient allocation with excess space above
        # the grid.
        #
        # Let the newly populated grid request its final geometry first, then
        # reveal it from the next main-loop iteration. Later redraws already have
        # established geometry and can be revealed immediately.
        if not getattr(self, "_featured_first_layout_committed", False):
            self._featured_first_layout_committed = True

            self.random_scripts_revealer.set_reveal_child(False)
            self.featured_scripts_revealer.set_reveal_child(False)

            # Attaching and showing the new grid children already invalidates GTK's
            # requisition chain. Avoid explicitly invalidating all four ancestors;
            # that only repeats the same size negotiation before the idle reveal.
            GLib.idle_add(self._reveal_initial_featured_layout)
        else:
            self.featured_scripts_revealer.set_reveal_child(True)
            self.random_scripts_revealer.set_reveal_child(True)

        return False

    def _refresh_random_scripts_display(self, force=False):
        """
        Recalculate and refresh the featured section.

        The first set reveals the whole section. Later replacements fade the cards
        out, swap them while hidden, then fade the replacement set in.
        """
        on_categories_view = (
            self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
        )

        if not self.all_scripts or not on_categories_view:
            # Navigation is not an invalidation event. A queued timer/resize callback
            # can arrive just after the stack changes, so simply stop here and keep
            # the existing cards intact for the next visit to the main menu.
            return False

        count = self._calculate_random_scripts_count()

        if count <= 0:
            # Temporarily hide when no complete row fits, but retain the chosen cards.
            self._hide_featured_section(discard=False)
            return True

        current_children = self.random_scripts_flowbox.get_children()
        layout = dict(getattr(self, "_featured_layout_metrics", {}) or {})
        layout_signature = (
            int(layout.get("rows", 0)),
            int(layout.get("columns", 0)),
            int(layout.get("large_count", 0)),
            count,
        )
        layout_changed = (
            layout_signature != getattr(self, "_featured_last_layout", None)
        )

        if (
            not force
            and not layout_changed
            and current_children
        ):
            self.featured_scripts_revealer.show_all()
            self.featured_scripts_revealer.set_reveal_child(True)
            self.random_scripts_revealer.set_reveal_child(True)
            return True

        scripts = self._select_random_scripts(count)

        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None

        if current_children and not layout_changed:
            # Timed content rotations keep the cosmetic cross-fade. Their geometry
            # is unchanged, so hiding/revealing the inner revealer cannot disturb
            # the section's vertical allocation.
            self._featured_swap_required_by_layout = False
            self.random_scripts_revealer.set_reveal_child(False)
            self._featured_swap_timer = GLib.timeout_add(
                self.FEATURED_SWAP_ANIMATION_MS,
                self._populate_random_scripts,
                scripts,
                count,
                layout,
            )
        else:
            # A settled resize that changes rows/columns is structural, not a
            # cosmetic card swap. Rebuilding through a hidden Gtk.Revealer left its
            # previous allocation in the surrounding vertical box for one layout
            # cycle, which is what produced the one-off title/card gap on the second
            # draw. Apply the final geometry immediately instead.
            self._featured_swap_required_by_layout = False
            self._populate_random_scripts(scripts, count, layout)
            if layout_changed:
                self.random_scripts_flowbox.queue_resize()
                self.featured_scripts_container.queue_resize()

        return True

    def _on_featured_size_allocate(self, _widget, _allocation):
        """
        Debounce resize events and update the featured layout after allocation.

        Returning to the main menu deliberately waits for this signal instead of
        measuring geometry from an idle callback. Gtk.Stack transitions can leave
        the categories view reporting its previous allocation for a short time;
        using that stale size caused a wrong Featured set to flash before the real
        allocation arrived.
        """
        if self.main_stack.get_visible_child_name() != "categories":
            return

        allocation_size = (
            max(0, int(getattr(_allocation, "width", 0))),
            max(0, int(getattr(_allocation, "height", 0))),
        )
        waiting_for_allocation = bool(
            getattr(self, "_featured_waiting_for_allocation", False)
        )
        if (
            allocation_size == getattr(self, "_featured_viewport_allocation", None)
            and not waiting_for_allocation
        ):
            return
        self._featured_viewport_allocation = allocation_size

        # Window owns the only responsive debounce timer. This signal is still
        # important for navigation back to the main menu, where the window itself
        # may not have changed size. A navigation return deliberately bypasses the
        # duplicate-allocation guard once via _featured_waiting_for_allocation.
        request_settle = getattr(self, "_request_window_resize_settle", None)
        if request_settle is not None:
            request_settle()
        else:
            self._apply_featured_resize()

    def _apply_featured_resize(self):
        """Apply the resize-triggered featured-section update using settled geometry."""
        self._featured_resize_timer = None

        if not (
            self.should_start_random_timer
            and self.all_scripts
            and self.main_stack.get_visible_child_name() == "categories"
        ):
            return False

        self._refresh_random_scripts_display(force=False)

        # A navigation return is complete only after a fresh allocation has been
        # observed. Start the periodic rotation from this settled state rather than
        # from the stale geometry that may still exist immediately after switching
        # Gtk.Stack children.
        if getattr(self, "_featured_waiting_for_allocation", False):
            self._featured_waiting_for_allocation = False
            self._restart_random_scripts_refresh_timer()

        return False

    def _on_featured_card_key_press(self, widget, event):
        """Keep keyboard activation available after moving Featured to Gtk.Grid."""
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self._activate_item(widget, event)
            return True
        return False

    def _on_featured_card_enter(self, _widget, _event):
        """Pause Featured rotation while the pointer is over a card."""
        self._featured_hovered = True

        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        # If the periodic timeout fired just before the pointer entered, cancel
        # that cosmetic replacement and keep the cards the user is reading. A
        # resize-driven swap is different: it is required to make the cards match
        # the newly available rows/columns, and maximizing/restoring the window can
        # itself generate enter events during GTK reallocation. Never cancel those.
        if (
            getattr(self, "_featured_swap_timer", None)
            and not getattr(self, "_featured_swap_required_by_layout", False)
        ):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None
            self._featured_swap_required_by_layout = False
            self.random_scripts_revealer.set_reveal_child(True)

        return False

    def _on_featured_card_leave(self, _widget, _event):
        """Resume Featured rotation with a fresh interval after hover ends."""
        self._featured_hovered = False

        if (
            self.should_start_random_timer
            and self.all_scripts
            and self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
            and not getattr(self, "_featured_waiting_for_allocation", False)
        ):
            self._restart_random_scripts_refresh_timer()

        return False

    def _get_featured_refresh_seconds(self):
        """Scale Featured rotation from 8s at <=10 cards to 15s at >=25 cards."""
        count = self._calculate_random_scripts_count()

        if count <= self.FEATURED_REFRESH_MIN_ITEMS:
            return self.FEATURED_REFRESH_MIN_SECONDS

        if count >= self.FEATURED_REFRESH_MAX_ITEMS:
            return self.FEATURED_REFRESH_MAX_SECONDS

        item_span = (
            self.FEATURED_REFRESH_MAX_ITEMS
            - self.FEATURED_REFRESH_MIN_ITEMS
        )
        time_span = (
            self.FEATURED_REFRESH_MAX_SECONDS
            - self.FEATURED_REFRESH_MIN_SECONDS
        )
        progress = (
            count - self.FEATURED_REFRESH_MIN_ITEMS
        ) / item_span

        return round(
            self.FEATURED_REFRESH_MIN_SECONDS
            + progress * time_span
        )

    def _periodic_random_scripts_refresh(self):
        """Rotate Featured once, then schedule the next dynamic interval."""
        self.random_scripts_refresh_timer = None
        self._refresh_random_scripts_display(force=True)

        if (
            self.should_start_random_timer
            and self.all_scripts
            and self.current_category_info is None
            and self.main_stack.get_visible_child_name() == "categories"
            and not getattr(self, "_featured_hovered", False)
            and not getattr(self, "_featured_waiting_for_allocation", False)
        ):
            self._restart_random_scripts_refresh_timer()

        # This timeout is intentionally one-shot. Recreating it after every
        # rotation lets the interval follow the current Featured item count.
        return False

    def _restart_random_scripts_refresh_timer(self):
        """Restart Featured rotation using the interval for the current card count."""
        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        # Hover owns the pause. The leave handler will start a completely fresh
        # interval, giving the user the full reading time after moving away.
        if getattr(self, "_featured_hovered", False):
            return

        refresh_seconds = self._get_featured_refresh_seconds()

        self.random_scripts_refresh_timer = GLib.timeout_add_seconds(
            refresh_seconds,
            self._periodic_random_scripts_refresh,
        )

    def _deferred_start_random_scripts_refresh_timer(self):
        """Populate Featured on initial startup once usable geometry exists."""
        if not self.featured_scripts_container or not self.all_scripts:
            return False

        if self.main_stack.get_visible_child_name() != "categories":
            return False

        # This path is for initial startup/data publication only. Navigation back to
        # the main menu is handled by _prepare_random_scripts_display(), which waits
        # for a fresh size-allocate signal before measuring anything.
        if getattr(self, "_featured_waiting_for_allocation", False):
            return False

        if (
            self.categories_view.get_allocated_height() <= 1
            or self.categories_flowbox.get_allocated_height() <= 1
        ):
            GLib.timeout_add(
                self.FEATURED_RESIZE_DEBOUNCE_MS,
                self._deferred_start_random_scripts_refresh_timer,
            )
            return False

        has_existing_cards = bool(self.random_scripts_flowbox.get_children())
        self._refresh_random_scripts_display(force=not has_existing_cards)
        self._restart_random_scripts_refresh_timer()
        return False

    def _prepare_random_scripts_display(self):
        """Resume Featured after navigation using the next real GTK allocation."""
        self.should_start_random_timer = True

        if not self.all_scripts:
            self.featured_scripts_revealer.set_reveal_child(False)
            return

        # Keep the previous cards alive, but do not reveal or recalculate them yet.
        # Gtk.Stack can briefly expose stale allocation values immediately after the
        # visible child changes. The next size-allocate callback is the first safe
        # point at which to calculate rows/columns for the returned main menu.
        self._featured_waiting_for_allocation = True
        self.random_scripts_revealer.set_reveal_child(False)
        self.featured_scripts_revealer.set_reveal_child(False)

        # Ensure GTK schedules a fresh allocation even when the window itself did
        # not change size while the category view was hidden in the stack.
        self.categories_view.queue_resize()
        self.categories_flowbox.queue_resize()

    def _stop_random_scripts_refresh_timer(self):
        """Stop featured-script refresh, resize and animation callbacks."""
        if self.random_scripts_refresh_timer:
            GLib.source_remove(self.random_scripts_refresh_timer)
            self.random_scripts_refresh_timer = None

        if getattr(self, "_featured_resize_timer", None):
            GLib.source_remove(self._featured_resize_timer)
            self._featured_resize_timer = None

        if getattr(self, "_featured_swap_timer", None):
            GLib.source_remove(self._featured_swap_timer)
            self._featured_swap_timer = None
        self._featured_swap_required_by_layout = False
