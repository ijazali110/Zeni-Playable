"""Staging-only playable artifact inspection. No user-provided success flag trusted."""
import io
import re
import zipfile
from html.parser import HTMLParser

MAX_BYTES=5*1024*1024
MAX_ZIP_UNCOMPRESSED=50*1024*1024
MAX_ZIP_MEMBERS=1000

class ArtifactError(ValueError): pass
class HTMLCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.has_html=False
        self.has_body=False
        self.scripts=0
    def handle_starttag(self,tag,attrs):
        if tag=="html": self.has_html=True
        if tag=="body": self.has_body=True
        if tag=="script": self.scripts+=1

def inspect_artifact(content,filename,network):
    if not isinstance(content,bytes) or not content:
        raise ArtifactError("empty export")
    if len(content)>MAX_BYTES:
        raise ArtifactError("export exceeds 5 MiB size cap")
    name=filename.lower()
    if name.endswith((".html",".htm")):
        html=content
        kind="html"
    elif name.endswith(".zip"):
        kind="zip"
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members=[f for f in archive.infolist() if not f.is_dir()]
                if len(members)>MAX_ZIP_MEMBERS:
                    raise ArtifactError("too many ZIP entries")
                if sum(f.file_size for f in members)>MAX_ZIP_UNCOMPRESSED:
                    raise ArtifactError("ZIP decompressed size exceeds cap")
                for f in members:
                    if f.filename.startswith(("/", "\\")) or ".." in f.filename.replace("\\","/").split("/"):
                        raise ArtifactError("unsafe ZIP entry")
                    if f.flag_bits & 1:
                        raise ArtifactError("encrypted ZIP entry")
                candidates=[f for f in members if f.filename.lower().endswith((".html",".htm"))]
                if not candidates:
                    raise ArtifactError("ZIP contains no playable HTML")
                chosen=next((f for f in candidates if f.filename.lower().endswith("/index.html") or f.filename.lower()=="index.html"),candidates[0])
                if chosen.file_size>MAX_BYTES: raise ArtifactError("HTML entry too large")
                html=archive.read(chosen)
        except (zipfile.BadZipFile,RuntimeError) as exc:
            raise ArtifactError("invalid ZIP package") from exc
    else:
        raise ArtifactError("HTML or ZIP required")
    if len(html)<64: raise ArtifactError("HTML unexpectedly small")
    try:
        source=html.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArtifactError("HTML is not valid UTF-8") from exc
    parser=HTMLCheck()
    parser.feed(source)
    if not parser.has_html or not parser.has_body:
        raise ArtifactError("missing HTML or BODY structure")
    if re.search(r"<script\\b",source,re.I) and "</script>" not in source.lower():
        raise ArtifactError("unclosed script element")
    return {"package":kind,"size":len(content),"html_size":len(html),
            "scripts":parser.scripts,"network":network,
            "validation":"structural_only","runtime_verified":False}
