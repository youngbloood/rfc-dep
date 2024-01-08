#!/usr/bin/python3
import json
from pyecharts import options as opts
from pyecharts.charts import Graph
import sys
import re
import webbrowser
from typing import Union
import requests

# flags
debug = False
auto_open = False
max_depth = 0
origin_rfc_num = 0

# RFC Class
class RFC(json.JSONDecoder,json.JSONEncoder):
    def __init__(
        self,
        # 协议名称
        name: str,
        # 被哪些协议更新
        updated_by: Union[list,None]=None,
        # 更新了哪些协议
        updates: Union[list,None]=None,
        # 被哪些协议淘汰
        obsoletes_by: Union[list,None]=None,
        # 淘汰了哪些协议
        obsoletes:Union[list,None]=None,
    ):
        self.name=str(name)
        self.url=f"https://www.rfc-editor.org/rfc/rfc{name}"
        self.title=""

        self.updated_by=[] if updated_by is None else updated_by
        self.updated_by_rfc=[]
        self.updates=[] if updates is None else updates
        self.updates_rfc=[]
        self.obsoletes_by=[] if obsoletes_by is None else obsoletes_by
        self.obsoletes_by_rfc=[]
        self.obsoletes=[] if obsoletes is None else obsoletes
        self.obsoletes_rfc=[]

        self.is_node_ranged = False
        self.is_link_ranged = False
        
    def __eq__(self, target: object) -> bool:
        if type(target) != type(self):
            return False
        return self.name==target.name
    
    def init(self):
        resp = requests.get(self.url)
        # print("resp = ",resp.text[:10000])
        # match title
        title_matched= re.findall(r'<span class="h1">(.*?)</span>',resp.text)
        if len(title_matched)>=1:
            self.title=str(title_matched[0])
        else:
            title_matched= re.findall(r'<h1 id="title">(.*?)</h1>',resp.text)
            if len(title_matched)>=1:
                self.title=str(title_matched[0])

        # match updated_by:
        updated_by_matched= re.findall(r"Updated by:(.*?)</a>[\n|\s]",resp.text)
        for v in updated_by_matched:
            updated_by_list=re.findall(r'target="_blank">(.*?)</a>',v+"</a>")
            for  u in updated_by_list:
                 self.updated_by.append(u)
        self.updated_by = sorted(list(set(self.updated_by)))

        # match updates:
        updates_matched= re.findall(r"Updates:(.*?)</a>[\n|\s]",resp.text)
        for v in updates_matched:
            updates_list=re.findall(r'/rfc(.*?)">',v+"</a>")
            for  u in updates_list:
                 self.updates.append(u)
        self.updates = sorted(list(set(self.updates)))

        # match obsolete_by:
        obsolete_by_matched= re.findall(r"Obsoleted by:(.*?)</a>[\n|\s]",resp.text)
        for v in obsolete_by_matched:
            obsoletes_list=re.findall(r'target="_blank">(.*?)</a>',v+"</a>")
            for  u in obsoletes_list:
                 self.obsoletes_by.append(u)
        self.obsoletes_by = sorted(list(set(self.obsoletes_by)))
        
        # match obsoletes:
        obsoletes_matched= re.findall(r"Obsoletes:(.*?)</a>[\n|\s]",resp.text)
        for v in obsoletes_matched:
            obsoletes_list=re.findall(r'/rfc(.*?[^target*])"',v+"</a>")
            for  u in obsoletes_list:
                 self.obsoletes.append(u)
        self.obsoletes = sorted(list(set(self.obsoletes)))
        
        if debug:
            print(f"rfc = {self.name}, updated_by = {self.updated_by}")
            print(f"rfc = {self.name}, updates = {self.updates}")
            print(f"rfc = {self.name}, obsoletes_by = {self.obsoletes_by}")
            print(f"rfc = {self.name}, obsoletes = {self.obsoletes}",)

        return self
    
    # return weather now rfc is obsoleted
    def is_obsoleted(self):
        return len(self.obsoletes_by)!=0
    
    # return weather now rfc is updated
    def is_updated(self):
        return len(self.updated_by)!=0
    
    def find_root(self):
        def min_rfc(update_rfcs :list):
            names = []
            for rfc in update_rfcs:
                names.append(rfc.name)
            min_rfc = min(names)
            for rfc in update_rfcs:
                if rfc.name == min_rfc:
                    return rfc
        
        updates_rfc = self.updates_rfc
        root_rfc = self
        while True:
            if debug:
                print(f"rfc_id = {root_rfc.name}, find_root.updates_rfc = {updates_rfc}")
            if len(updates_rfc) == 0:
                break
            _root_rfc = min_rfc(updates_rfc)
            if root_rfc == _root_rfc:
                break
            root_rfc=_root_rfc
            updates_rfc = _root_rfc.updates_rfc
        return root_rfc
    
    def gen_categories(self):
        return ["obsoleted","updated","latest"]

    def __get_echart_node(self):
        item_style = opts.ItemStyleOpts()
        if str(self.name) == str(origin_rfc_num): # red
            item_style = opts.ItemStyleOpts(color="#FF0000")
        elif len(self.obsoletes_by_rfc) != 0 or len(self.obsoletes_by) != 0: # gray
            item_style = opts.ItemStyleOpts(color="#9999CC")
        else: # green
            item_style = opts.ItemStyleOpts(color="#80FF00")
        return opts.GraphNode(name=self.name, 
                              symbol_size=70,
                              value=self.title,
                              itemstyle_opts=item_style,
                              )
    
    # 循环引用可能造成：RecursionError: maximum recursion depth exceeded
    # nodem: 存储rfc节点信息： rfc_id: *rfc
    # is_node_ranged: 标识该rfc节点是否已经被遍历过了
    def __gen_nodes(self, nodem = {}):
        if self.is_node_ranged is False:
            self.is_node_ranged = True
            nodem[self.name]=self
        else:
            return
        
        def closure(rfcs: list):
            for v in rfcs:
                v.__gen_nodes(nodem)
        closure(self.updated_by_rfc)
        closure(self.updates_rfc)
        closure(self.obsoletes_by_rfc)
        closure(self.obsoletes_rfc)

    def gen_nodes(self):
        nodem = {}
        self.__gen_nodes(nodem)
        nodes = []
        all_nodes = nodem.values()
        sorted(all_nodes,key=lambda x:x.name)
        for v in all_nodes:
            nodes.append(v.__get_echart_node())
        return nodes

        
    # @inline
    # def __get_echart_link(name1: str,name2: str):
    #     return opts.GraphLink(source=str(name1), target=str(name2), value=2)

    # is_link_ranged: 标识该rfc节点与其相关rfc节点的link连接是否已经遍历过了
    def __gen_links(self,linksm = {}):
        if self.is_link_ranged is False:
            self.is_link_ranged = True
        else:
            return
        # 构建self与updated_by_rfc，updates_rfc，obsoletes_by_rfc，obsoletes_rfc的link映射
        def closure(rfcs: list,relation: str):
            for v in rfcs:
                name_min,name_max = min(self.name,v.name),max(self.name,v.name)
                key = (name_min, name_max)
                linksm[key]=relation

        closure(self.updated_by_rfc,"updated_by")
        closure(self.updates_rfc,"updated_by")
        closure(self.obsoletes_by_rfc,"obsolete_by")
        closure(self.obsoletes_rfc,"obsolete_by")

        # 递归构建updated_by_rfc，updates_rfc，obsoletes_by_rfc，obsoletes_rfc下的映射
        def cycle_closure(rfcs: list):
            for v in rfcs:
                v.__gen_links(linksm)

        cycle_closure(self.updated_by_rfc)
        cycle_closure(self.updates_rfc)
        cycle_closure(self.obsoletes_by_rfc)
        cycle_closure(self.obsoletes_rfc)

    def gen_links(self,linksm = {}):
        links = []
        linksm = {}
        self.__gen_links(linksm)
        for (name1,name2),relation in linksm.items():
            line_style = opts.LineStyleOpts()
            if relation == "updated_by": # blue
                line_style = opts.LineStyleOpts(color="#66CCCC")
            else: # red
                line_style = opts.LineStyleOpts(color="#FF0000")
            links.append(opts.GraphLink(source=str(name1), target=str(name2), value=str(relation),linestyle_opts=line_style))
        return links


    def gen_relation_html(self):
        nodes = self.gen_nodes()
        links = self.gen_links()
        c = (
            Graph(init_opts=opts.InitOpts(width="2000px", height="2000px"))
            .add("", nodes, links,repulsion = "200")
            .set_global_opts(title_opts=opts.TitleOpts(title=f"RFC{origin_rfc_num}-DEPTH-{max_depth}"))
            .render(f"./examples/rfc{origin_rfc_num}-depth-{max_depth}-dependency.html")
        )
        if auto_open:
             webbrowser.open(f"./examples/rfc{origin_rfc_num}-dependency.html")


def deep_qeury(rfc_num: str,depth=0, m: dict={}):
    if max_depth !=0 and depth >= max_depth:
        return None
    if rfc_num in m.keys():
        return m[rfc_num]
    if debug:
        print("\nrfc id = ",rfc_num)
    rfc = RFC(rfc_num).init()
    m[rfc_num] = rfc
    
    for name in rfc.updated_by:
        if name in m.keys():
            rfc.updated_by_rfc.append(m[name])
            continue
        updated_by = deep_qeury(name,depth+1,m)
        if updated_by is not None:
            rfc.updated_by_rfc.append(updated_by)
    
    for name in rfc.updates:
        if name in m.keys():
            rfc.updates_rfc.append(m[name])
            continue
        update = deep_qeury(name,depth+1,m)
        if update is not None:
            rfc.updates_rfc.append(update)

    for name in rfc.obsoletes_by:
        if name in m.keys():
            rfc.obsoletes_by_rfc.append(m[name])
            continue
        obsoleted_by = deep_qeury(name,depth+1,m)
        if obsoleted_by is not None:
            rfc.obsoletes_by_rfc.append(obsoleted_by)

    for name in rfc.obsoletes:
        if name in m.keys():
            rfc.obsoletes_rfc.append(m[name])
            continue
        obsolete = deep_qeury(name,depth+1,m)
        if obsolete is not None:
            rfc.obsoletes_rfc.append(obsolete)

    return rfc



def parse_flag():
    if len(sys.argv) < 2:
        print("Must specify the rfc protocol number(the first args)")
        sys.exit(1)

    global origin_rfc_num
    origin_rfc_num = int(sys.argv[1])

    if len(sys.argv)<3:
        return
    
    for arg in sys.argv[2:]:
        if arg == "--debug":
            global debug
            debug = True
        if arg.startswith("--depth="):
            global max_depth
            max_depth = int(arg.lstrip("--depth="))
        if arg == "--auto-open":
            global auto_open
            auto_open = True
    print(f"max_depth={max_depth},auto_open={auto_open},debug={debug}")
    

if __name__=="__main__":
    parse_flag()
    
    rfc = deep_qeury(str(origin_rfc_num))
    root = rfc.find_root()
    root.gen_relation_html()

