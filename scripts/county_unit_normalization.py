"""Small, conservative helpers for counted Chinese county-level lists.

Historical administrative notices often write ``甲、乙二县`` instead of
repeating ``县`` after every name.  The count belongs to the list, not to the
last name.  This module normalizes only structured/search fields; the source
sentence is always kept verbatim in ``change_description``.
"""

from __future__ import annotations

import re


UNIT_SUFFIXES = (
    "自治县", "自治旗", "县级市", "市辖区", "林区", "特区", "市", "县", "区", "旗",
)

# The suffix after the count may itself contain a modifier, e.g.
# ``两个彝族自治县``.
COUNTED_UNIT_RE = re.compile(
    r"^(?P<prefix>.*?)(?P<qualifier>共|等)?"
    r"(?P<count>两|[一二三四五六七八九十百]+|[0-9]+)(?:个)?"
    r"(?P<suffix>(?:(?:蒙古族|回族|彝族|藏族|羌族|苗族|土家族|瑶族|壮族|布依族|哈尼族|哈萨克族|柯尔克孜族|锡伯族|东乡族|保安族|仫佬族|毛南族|侗族|纳西族|傈僳族|景颇族|德昂族|阿昌族|普米族|拉祜族|佤族|白族|满族|朝鲜族|达斡尔族|鄂温克族|鄂伦春族)自治县|自治旗|县级市|市辖区|林区|特区|市|县|区|旗))$"
)

NOISE_MARKERS = (
    "行政", "区域", "并入", "划归", "管辖", "设立", "撤销", "撤消", "原属",
    "国务院", "关于", "批复", "同意", "调整", "地级市", "升为", "部分",
    "公社", "大队", "生产队", "变更", "实行", "以原", "为",
)


def normalize_unit_name(value: str) -> str:
    """Return a canonical unit name, or an empty string for a count-only token."""

    value = re.sub(r"[（(][^）)]*[）)]", "", value)
    value = value.strip(" ，。、；：:|")
    if not value:
        return ""

    # A source clause may qualify a county with its former parent, e.g.
    # ``楚雄彝族自治州的禄劝县``.  The searchable field needs the unit itself.
    value = re.sub(r"^.*?(?:地区|自治区|自治州直辖|自治州|市|县)的", "", value)
    if value.startswith("原"):
        for suffix in UNIT_SUFFIXES:
            core = value[1:]
            if core.endswith(suffix) and len(core[:-len(suffix)]) >= 2:
                value = core
                break

    match = COUNTED_UNIT_RE.fullmatch(value)
    if not match:
        return value

    prefix = match.group("prefix").rstrip("的")
    prefix = re.sub(r"(?:共|等)$", "", prefix)
    if not prefix or any(marker in prefix for marker in NOISE_MARKERS):
        return ""

    suffix = match.group("suffix")
    # ``张家川回族自治县五县`` is a malformed count attachment, not a
    # request to append a second ``县``.
    if prefix.endswith(UNIT_SUFFIXES):
        return prefix
    return prefix + suffix


def is_counted_unit_phrase(value: str) -> bool:
    value = re.sub(r"[（(][^）)]*[）)]", "", value).strip(" ，。、；：:|")
    return bool(COUNTED_UNIT_RE.fullmatch(value))


def normalize_unit_list(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = normalize_unit_name(value)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def split_counted_group(value: str) -> list[str]:
    """Expand a list whose final item carries the shared unit suffix.

    Examples::

        丰润、丰南、乐亭十县 -> 丰润县、丰南县、乐亭县
        临潼、蓝田二县 -> 临潼县、蓝田县
        金门（待回归）等七县 -> 金门县
    """

    value = value.strip(" ，。、；：:")
    if not value:
        return []
    separators = r"[、,，]|(?<=[县市区旗])和(?=[\u4e00-\u9fff])|及|与"
    parts = [part.strip(" 的") for part in re.split(separators, value) if part.strip(" 的")]
    if not parts:
        return []

    shared_suffix = ""
    for part in parts:
        match = COUNTED_UNIT_RE.fullmatch(re.sub(r"[（(][^）)]*[）)]", "", part).strip(" 的"))
        if match:
            shared_suffix = match.group("suffix")
            break
        normalized = normalize_unit_name(part)
        if normalized.endswith(UNIT_SUFFIXES):
            shared_suffix = next(suffix for suffix in UNIT_SUFFIXES if normalized.endswith(suffix))

    result: list[str] = []
    for part in parts:
        cleaned = re.sub(r"[（(][^）)]*[）)]", "", part).strip(" 的")
        cleaned = re.sub(r"^.*?(?:地区|省|自治区|自治州直辖|自治州|市)的", "", cleaned)
        if any(marker in cleaned for marker in NOISE_MARKERS):
            continue
        normalized = normalize_unit_name(cleaned)
        if normalized:
            if shared_suffix and not normalized.endswith(UNIT_SUFFIXES):
                normalized += shared_suffix
            elif not normalized.endswith(UNIT_SUFFIXES):
                continue
            if normalized not in result:
                result.append(normalized)
            continue
        if shared_suffix and re.fullmatch(r"[\u4e00-\u9fff]{1,12}", cleaned):
            candidate = cleaned if cleaned.endswith(UNIT_SUFFIXES) else cleaned + shared_suffix
            if candidate not in result:
                result.append(candidate)
    return result


def extract_counted_source_units(text: str) -> list[str]:
    """Recover names from transfer clauses such as ``将甲、乙二县划归丙市``."""

    result: list[str] = []
    # A semicolon-delimited source clause is enough for the early notices and
    # avoids interpreting legal prose such as ``国务院关于……六个市`` as a unit.
    pattern = re.compile(
        r"(?:将|以)(?P<left>[^；。]+?)(?:划归|并入|改为|更名为|的部分行政区域)"
    )
    for match in pattern.finditer(text):
        left = match.group("left")
        if any(marker in left for marker in ("公社", "大队", "生产队", "行政区域")):
            continue
        left = re.sub(r"(?:[^、和及与]*?(?:地区|省|自治区))的", "", left)
        result.extend(split_counted_group(left))
    # ``以保亭、琼中、乐东三县的部分行政区域`` is not a transfer verb,
    # but follows the same counted-list grammar.
    for match in re.finditer(r"以(?P<left>[^；。]+?)的部分行政区域", text):
        left = re.sub(r"(?:[^、和及与]*?(?:地区|省|自治区))的", "", match.group("left"))
        result.extend(split_counted_group(left))
    return list(dict.fromkeys(result))
