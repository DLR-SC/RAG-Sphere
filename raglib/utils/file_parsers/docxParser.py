from xml.etree import ElementTree as ET
from zipfile import ZipFile
from pathlib import Path
from re import sub

# Constant values used in the word xml representation
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML = "http://www.w3.org/XML/1998/namespace"

_TAGS = {
    f"{{{_W}}}b": "b",
    f"{{{_W}}}sz": "sz",
    f"{{{_W}}}szCs": "sz",
    f"{{{_W}}}p": "p",
    f"{{{_W}}}pPr": "pPr",
    f"{{{_W}}}rPr": "rPr",
    f"{{{_W}}}r": "r",
    f"{{{_W}}}t": "t",
    f"{{{_W}}}br": "br",
    f"{{{_W}}}numPr": "numPr",
    f"{{{_W}}}ilvl": "ilvl",
    f"{{{_W}}}numId": "numId",
    f"{{{_W}}}lastRenderedPageBreak": "lastRenderedPageBreak",
    f"{{{_W}}}tab": "tab",
    f"{{{_W}}}tbl": "tbl",
    f"{{{_W}}}tblGrid": "tblGrid",
    f"{{{_W}}}gridCol": "gridCol",
    f"{{{_W}}}tr": "tr",
    f"{{{_W}}}tc": "tc",
    f"{{{_W}}}tcPr": "tcPr",
    f"{{{_W}}}gridSpan": "gridSpan",
    f"{{{_W}}}basedOn": "basedOn",
    f"{{{_W}}}next": "nextStyle",
    f"{{{_W}}}pStyle": "pStyle",
    f"{{{_W}}}tblPr": "tblPr",
    f"{{{_W}}}tblStyle": "tblStyle",
    f"{{{_W}}}bCs": None,
    f"{{{_W}}}tblW": None,
    f"{{{_W}}}tblLook": None,
    f"{{{_W}}}tcW": None,
    f"{{{_W}}}shd": None,
    f"{{{_W}}}jc": None,
    f"{{{_W}}}proofErr": None,
    f"{{{_W}}}spacing": None,
    f"{{{_W}}}lang": None,
    f"{{{_W}}}noProof": None,
    f"{{{_W}}}drawing": None,
    f"{{{_W}}}ind": None,
    f"{{{_W}}}rFonts": None,
    f"{{{_W}}}fldChar": None,
    f"{{{_W}}}instrText": None,
    f"{{{_W}}}bookmarkStart": None,
    f"{{{_W}}}bookmarkEnd": None,
    f"{{{_W}}}tcBorders": None,
    f"{{{_W}}}vAlign": None,
    f"{{{_W}}}color": None,
    f"{{{_W}}}sectPr": None,
    f"{{{_W}}}name": None,
    f"{{{_W}}}qFormat": None,
    f"{{{_W}}}link": None,
    f"{{{_W}}}uiPriority": None,
    f"{{{_W}}}unhideWhenUsed": None,
    f"{{{_W}}}rsid": None,
    f"{{{_W}}}tabs": None,
    f"{{{_W}}}semiHidden": None,
    f"{{{_W}}}tblInd": None,
    f"{{{_W}}}tblCellMar": None,
    f"{{{_W}}}tblBorders": None,
}

class XML_Parser:
    def __init__(self, doc_root : ET, style_root : ET):
        self.content = list()
        self._current_page = list()
        self._numbers = dict()

        self.doc_root = doc_root
        self.style_root = style_root   
        self.style_properties = dict()

    def _get_style_property(self, styleId: str):
        if styleId in self.style_properties: return self.style_properties[styleId]

        style_properties = self.style_properties["__default"].copy()
        self._parse_xml(self.style_root.find(f"./w:style[@w:styleId=\"{styleId}\"]", {'w': _W}), style_properties)

        self.style_properties[styleId] = style_properties
        return style_properties
    
    def _parse_xml(self, root : ET, properties : dict):
        for element in root:
            if not element.tag in _TAGS:
                continue
                print(self._current_page)
                print(properties)
                raise NotImplementedError(f"Element tag {element.tag} not yet implemented!")

            match _TAGS[element.tag]:
                case None:
                    continue

                case "p":
                    if self._current_page:
                        self._current_page.append({"Text": "\n", "FontSize": -1, "IsBold": False})
                    props = self._get_style_property(properties.get("Style", "__default")) | properties
                    self._parse_xml(element, props)
                    properties["Style"] = self._get_style_property(props.get("Style", "__default")).get("Next", "__default")

                case "pPr":
                    self._parse_xml(element, properties)
                case "pStyle":
                    properties["Style"] = element.attrib.get(f"{{{_W}}}val", "__default")
                case "rPr":
                    self._parse_xml(element, properties)
                case "b":
                    properties["isBold"] = True
                case "sz":
                    properties["sz"] = int(element.attrib.get(f"{{{_W}}}val", "-1").strip() or "-1")
                case "r":
                    self._parse_xml(element, self.style_properties["__default"] | properties)
                    # Reset once per Paragraph variables
                    properties["numId"] = -1
                case "t":
                    if (ilvl := properties.get("ilvl", 0)) > 0 and (not self._current_page or self._current_page[-1].get("Text","#")[-1] == "\n"):
                        self._current_page.append({"Text": "\t" * ilvl, "FontSize": properties.get("sz", -1), "IsBold": properties.get("isBold", False)})

                    if (numId := properties.get("numId", -1)) >= 0:
                        self._numbers[(numId, ilvl)] = (number := self._numbers.get((numId, ilvl), 1)) + 1
                        self._current_page.append({"Text": f"{number}. ", "FontSize": properties.get("sz", -1), "IsBold": properties.get("isBold", False)})

                    # Add text
                    text = element.text
                    if element.attrib.get(f"{{{_XML}}}space", None) != "preserve": text = text.strip()
                    self._current_page.append({"Text": text, "FontSize": properties.get("sz", -1), "IsBold": properties.get("isBold", False)})
                case "tab":
                    self._current_page.append({"Text": "\t", "FontSize": -1, "IsBold": False})
                case "br":
                    match element.attrib.get(f"{{{_W}}}type", "textWrapping"):
                        case "textWrapping":
                            pass
                        case "page":
                            self.content.append(self._current_page)
                            self._current_page = list()
                        case "column":
                            raise NotImplementedError(f"Break {element.attrib} not yet implemented!")
                case "numPr":
                    self._parse_xml(element, properties)
                case "numId":
                    properties["numId"] = int(element.attrib.get(f"{{{_W}}}val", "-1").strip() or "-1")
                case "ilvl":
                    properties["ilvl"] = int(element.attrib.get(f"{{{_W}}}val", "0").strip() or "0")
                case "lastRenderedPageBreak":
                    if self._current_page:
                        self.content.append(self._current_page)
                        self._current_page = list()

                case "tbl":
                    props = properties.copy()
                    props["ColumnCount"] = 0
                    props["Table"] = list()
                    props["Row"] = list()
                    self._parse_xml(element, props)
                    self._current_page.extend([
                        {"Text": "\n", "FontSize": -1, "IsBold": False},
                        {"Table": props.get("Table", list()), "FontSize": -1, "IsBold": False},
                        {"Text": "\n", "FontSize": -1, "IsBold": False},
                    ])
                case "tblPr":
                    self._parse_xml(element, properties)
                case "tblStyle":
                    properties["Style"] = element.attrib.get(f"{{{_W}}}val", "__default")
                case "tblGrid":
                    self._parse_xml(element, properties)
                case "gridCol":
                    properties["ColumnCount"] = properties.get("ColumnCount", 0) + 1
                case "tr":
                    content, _current_page = self.content, self._current_page
                    self.content, self._current_page = list(), list()

                    self._parse_xml(element, properties)
                    if (row := properties.get("Row", None)):
                        properties.setdefault("Table", list()).append(row)
                    properties["Row"] = list()

                    self.content, self._current_page = content, _current_page
                case "tc":
                    props = properties.copy()
                    props["gridSpan"] = 1
                    self._parse_xml(element, props)
                    for _ in range(props.get("gridSpan", 1)):
                        properties.setdefault("Row", list()).append(self._current_page)
                    self._current_page = list()
                case "tcPr":
                    self._parse_xml(element, properties)
                case "gridSpan":
                    properties["gridSpan"] = int(element.attrib.get(f"{{{_W}}}val", "1").strip() or "1")

                case "basedOn":
                    base_style = self._get_style_property(element.attrib.get(f"{{{_W}}}val", "__default"))
                    for key, item in base_style.items():
                        if not key in properties: properties[key] = item
                case "nextStyle":
                    properties["Next"] = element.attrib.get(f"{{{_W}}}val", "__default")

    def parse_xml(self):
        body = self.doc_root.find("./w:body", {'w': _W})
        
        default_style_properties = dict()
        self._parse_xml(self.style_root.find(f"./w:docDefaults/w:pPrDefault", {'w': _W}), default_style_properties)
        self._parse_xml(self.style_root.find(f"./w:docDefaults/w:rPrDefault", {'w': _W}), default_style_properties)
        self.style_properties["__default"] = default_style_properties

        self._parse_xml(body, {"Style": "__default"})
        self.content.append(self._current_page)
        return self
    
    def get_markdown(self):
        content_stack = list()
        for page in self.content: content_stack.extend(page)

        total_chars = 0
        font_sizes = dict()

        while content_stack:
            element = content_stack.pop()

            if "Table" in element:
                for row in element["Table"]:
                    row_copy = row.copy()
                    row.clear()

                    for cell in row_copy:
                        text, min_size, isBold = "", -1, False
                        for content in cell:
                            if isBold != content["IsBold"] and content["FontSize"] >= 0:
                                text += "**"
                                isBold ^= True
                            
                            text += content["Text"].replace("*", "\*")
                            if content["FontSize"] != -1:
                                min_size = min(min_size, content["FontSize"]) if min_size != -1 else content["FontSize"]
                        if isBold: text += "**"
                        if min_size == -1:
                            row.append({"Text": "", "FontSize": -1, "IsBold": False})
                        else:
                            row.append({"Text": text, "FontSize": min_size, "IsBold": False})
                continue

            if element["FontSize"] == -1: continue

            total_chars += len(element["Text"])
            font_sizes[element["FontSize"]] = font_sizes.get(element["FontSize"], 0) + len(element["Text"])

        font_size_counts = list(font_sizes.items())
        font_size_counts.sort(key = lambda f: f[0])

        count_min = int(total_chars * 0.001)

        header_lvl = 4
        char_count = 0

        for size, count in font_size_counts:
            if count > count_min and char_count > 0.5 * total_chars:
                header_lvl = max(header_lvl - 1, 1)
                total_chars -= char_count
                char_count = 0

            char_count += count
            font_sizes[size] = header_lvl

        final_pages = []
        for page in self.content:
            header_level = 4
            is_bold = False
            final_page = ""

            for content in page:
                if "Table" in content: 
                    if is_bold: final_page += "**"
                    final_page += "\n|" 
                    final_page += "|".join(cell["Text"].replace("\n", "<br>").replace("|", "\|") for cell in content["Table"][0]) + "|\n"
                    final_page += "|" + "-------|" * len(content["Table"][0]) + "\n"
                    for row in content["Table"][1:]:
                        final_page += "|" + "|".join(cell["Text"].replace("\n", "<br>").replace("|", "\|") for cell in row) + "|\n"
                    final_page += "\n"
                else:
                    if content["FontSize"] >= 0 and header_level != font_sizes[content["FontSize"]]:
                        if is_bold: final_page += "**"
                        
                        final_page += "\n\n"
                        header_level = font_sizes[content["FontSize"]]
                        is_bold = content["IsBold"]
                        if header_level != 4:
                            final_page += "#" * header_level + " "
                        
                        if is_bold: final_page += "**"
                        final_page += content["Text"].replace("*", "\*").replace("|", "\|")
                    else:
                        if is_bold != content["IsBold"]: final_page += "**"
                        is_bold = content["IsBold"]
                        final_page += content["Text"].replace("*", "\*").replace("|", "\|")

            final_page = final_page.replace("**\n", "**\n\n")
            final_page = final_page.replace("\n**", "\n\n**")
            final_page = sub("\n\n+", "\n\n", final_page).lstrip("\n").rstrip("\n")
            final_page = sub("\.\.\.+", "...", final_page)
            final_page = sub(" +", " ", final_page)
            final_page = final_page.replace(" **\n", "**\n")
            final_page = final_page.replace("# ** ", "# **")
            final_page = final_page.replace("# **\t", "# **")
            final_page = final_page.replace("** **", " ")
            final_page = final_page.replace("**\t**", "\t")
            final_page = final_page.replace("**\n**", "\n")
            final_page = final_page.replace("****", "")
            final_pages.append(final_page)

        return final_pages

def parse_docx(path : Path) -> [str]:
    """
    Reads the content of a .docx file and parses them into markdown format.

    Parameters:
    - path (Path): the path to the .docx file

    Returns:
    A list of markdown strings where each entry approximatly (not really) corresponds to a page.
    """
    with ZipFile(path) as doc_zip:
        doc_xml = doc_zip.read("word/document.xml")
        sty_xml = doc_zip.read("word/styles.xml")

        doc_root = ET.fromstring(doc_xml)
        sty_root = ET.fromstring(sty_xml)

        return XML_Parser(doc_root, sty_root).parse_xml().get_markdown()