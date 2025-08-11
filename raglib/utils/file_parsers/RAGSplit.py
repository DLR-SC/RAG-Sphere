from typing import (
    Dict,
    List,
    Any
)

# The maximum number of characters a body text may have
_MAX_BODY_LEN = 4096

def split(
    data : List[str],
    max_chunk_size: int = _MAX_BODY_LEN
) -> List[Dict]:
    """
    Splits the provided pages of strings into sections for paragraphs and additional splits for too long text

    Parameters:
    data ([str]): A list of markdown formattet string, where each element represents a single page

    Returns: a list of text split element dicts with the fields: b"h1", b"h2", b"h3", b"body", b"ref", b"Content" and b"PageHint"
    """
    # Splits all pages into its overall sections seperated by 2 newlines
    line_splits = (page.split("\n\n") for page in data)
    
    # Adds values to be populated by the content
    h1, h2, h3, body = "", "", "", ""
    pages, last = set(), 1

    # Adds a list of resulting text splits
    results = list()

    # Add and identify the content of all sections on all pages
    for idx, page_split in enumerate(line_splits):
        # Check each section in the page
        for line in page_split:
            # Section is a h1 header
            if line.startswith("# "):
                if last == 1:
                    h1 = h1 + " " + line[2:].strip() if h1 else line[2:].strip()
                else:
                    if last == 4:
                        results.append({
                            b'h1' : h1,
                            b'h2' : h2,
                            b'h3' : h3,
                            b'body' : body,
                            b'ref' : list(pages)
                        })
                        pages = set()

                    h1 = line[2:].strip()
                    h2, h3, body = "", "", ""
                    last = 1
            # Section is a h2 header
            elif line.startswith("## "):
                if last == 2:
                    h2 = h2 + " " + line[3:].strip() if h2 else line[3:].strip()
                else:
                    if last == 4:
                        results.append({
                            b'h1' : h1,
                            b'h2' : h2,
                            b'h3' : h3,
                            b'body' : body,
                            b'ref' : list(pages)
                        })
                        pages = set()
                    
                    h2 = line[3:].strip()
                    h3, body = "", ""
                    last = 2
            # Section is a h3 header
            elif line.startswith("### "):
                if last == 3:
                    h3 = h3 + " " + line[4:].strip() if h3 else line[4:].strip()
                else:
                    if last == 4:
                        results.append({
                            b'h1' : h1,
                            b'h2' : h2,
                            b'h3' : h3,
                            b'body' : body,
                            b'ref' : list(pages)
                        })
                        pages = set()
                    
                    h3 = line[4:].strip()
                    body = ""
                    last = 3
            # Section is a text body
            else:
                if last == 4:
                    line = line.strip()
                    if body and len(body) + len(line) > max_chunk_size:
                        results.append({
                            b'h1' : h1,
                            b'h2' : h2,
                            b'h3' : h3,
                            b'body' : body,
                            b'ref' : list(pages)
                        })
                        pages = {idx}
                        body = line

                    else:
                        body = body + "\n\n" + line if body else line
                else:
                    body = line.strip()
                    last = 4
                pages |= {idx}

    # Append the last text section to the list of results
    if last == 4:
        results.append({
            b'h1' : h1,
            b'h2' : h2,
            b'h3' : h3,
            b'body' : body,
            b'ref' : list(pages)
        })
    
    for result in results:
        # Squash the headers and body into a single content string in markdown format
        content = ""
        if result[b'h1']: content += "# " + result[b'h1'] + "\n\n"
        if result[b'h2']: content += "## " + result[b'h2'] + "\n\n"
        if result[b'h3']: content += "### " + result[b'h3'] + "\n\n"
        content += result[b'body']

        result[b'Content'] = content

        # Add a page hint to reflect the page the body has content from
        result[b'PageHint'] = f"Page ({result[b'ref'][0] + 1})" if len(result[b'ref']) == 1 \
            else f"Pages ({result[b'ref'][0] + 1}-{result[b'ref'][-1] + 1})"
    
    return results