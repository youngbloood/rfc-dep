#!/usr/bin/python3
import json
import simplejson
from pyecharts import options as opts
from pyecharts.charts import Graph
import sys
import re
import webbrowser
from typing import Union
import requests

debug = False
auto_open = False
max_depth = 2
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
        self.name=name
        self.url=f"https://www.rfc-editor.org/rfc/rfc{name}"

        self.updated_by=[] if updated_by is None else updated_by
        self.updated_by_rfc=[]
        self.updates=[] if updates is None else updates
        self.updates_rfc=[]
        self.obsoletes_by=[] if obsoletes_by is None else obsoletes_by
        self.obsoletes_by_rfc=[]
        self.obsoletes=[] if obsoletes is None else obsoletes
        self.obsoletes_rfc=[]
        
    def __eq__(self, target: object) -> bool:
        if type(target) != type(self):
            return False
        return self.name==target.name
    
    def init(self):
        resp = requests.get(self.url)
        # print("resp = ",resp.text[:10000])
        # match updated_by:
        updated_by_matched= re.findall(r"Updated by:(.*?)</a>[\n|\s]",resp.text)
        for v in updated_by_matched:
            updated_by_list=re.findall(r'target="_blank">(.*?)</a>',v+"</a>")
            for  u in updated_by_list:
                 self.updated_by.append(u)

        # match updates:
        updates_matched= re.findall(r"Updates:(.*?)</a>[\n|\s]",resp.text)
        for v in updates_matched:
            updates_list=re.findall(r'/rfc(.*?)">',v+"</a>")
            for  u in updates_list:
                 self.updates.append(u)

        # match obsolete_by:
        obsolete_by_matched= re.findall(r"Obsoleted by:(.*?)</a>[\n|\s]",resp.text)
        for v in obsolete_by_matched:
            obsoletes_list=re.findall(r'target="_blank">(.*?)</a>',v+"</a>")
            for  u in obsoletes_list:
                 self.obsoletes_by.append(u)

        # match obsoletes:
        obsoletes_matched= re.findall(r"Obsoletes:(.*?)</a>[\n|\s]",resp.text)
        for v in obsoletes_matched:
            obsoletes_list=re.findall(r'/rfc(.*?[^target*])"',v+"</a>")
            for  u in obsoletes_list:
                 self.obsoletes.append(u)

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
                print(f"rfc_id = {root_rfc.name}, find_root.updates_rfc = {updates_rfc}",)
            if len(updates_rfc) == 0:
                break
            _root_rfc = min_rfc(updates_rfc)
            if root_rfc == _root_rfc:
                break
            root_rfc=_root_rfc
            updates_rfc = _root_rfc.updates_rfc
        return root_rfc
    
    def gen_nodes_links(self):
        categories = ["obsoleted","updated","latest"]
        nodes = []
        links = []

        all_rfc = {}
        m = {}
        pair = {}

        def add_to_all(rfcs : list):
            for v in rfcs:
                all_rfc[v.name]=v
                
        add_to_all(self.updated_by_rfc)
        add_to_all(self.updates_rfc)
        add_to_all(self.obsoletes_by_rfc)
        add_to_all(self.obsoletes_rfc)

        def add_nodes_links(rfcs : list):
            for v in rfcs:
                ## add node
                if v.name in m.keys():
                    continue
                m[v.name] = v

                category = 0
                show = True
                if v.is_obsoleted():
                    show = False
                if v.is_updated():
                    category = 1
                if len(v.updated_by) == 0:
                    category = 2

                nodes.append(opts.GraphNode(name=v.name, symbol_size=20,value=v.url,label_opts={"normal":{"show":show}},category=category))

                ## add link
                if f"{self.name}-{v.name}" in pair.keys() or f"{v.name}-{self.name}" in pair.keys():
                    continue
                pair[f"{self.name}-{v.name}"]=True
                links.append(opts.GraphLink(source=self.name, target=v.name, value=2))

        add_nodes_links(self.updated_by_rfc)
        add_nodes_links(self.updates_rfc)
        add_nodes_links(self.obsoletes_by_rfc)
        add_nodes_links(self.obsoletes_rfc)

        return categories,nodes,links

    def gen_relation_html(self):
        _,nodes,links = self.gen_nodes_links()
        c = (
            Graph()
            .add("", nodes, links, repulsion=400)
            .set_global_opts(title_opts=opts.TitleOpts(title="Graph-GraphNode-GraphLink"))
            .render("graph_with_options.html")
        )
        if auto_open:
             webbrowser.open("graph_with_options.html")
    
    def gen_relation_html_with_les_miserables(self):
        categories,nodes,links = self.gen_nodes_links()
        c = (
            Graph(init_opts=opts.InitOpts(width="2000px", height="2000px"))
            .add(
                "random",
                nodes=nodes,
                links=links,
                categories=categories,
                layout="circular",
                is_rotate_label=True,
                linestyle_opts=opts.LineStyleOpts(color="source", curve=0.3),
                label_opts=opts.LabelOpts(position="right"),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="Graph-Les Miserables"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="2%", pos_top="20%"),
            )
            .render("graph_les_miserables.html")
        )

        

        


def deep_qeury(rfc_num: str,depth=0, m: dict={}):
    if depth >= max_depth:
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



if __name__=="__main__":
    if len(sys.argv) < 2:
        print("Must specify the rfc protocol number(the first args)")
        sys.exit(1)
    if len(sys.argv)==3:
        debug=bool(sys.argv[2])
        print(f"debug is {debug}")

    rfc_num = int(sys.argv[1])
    rfc = deep_qeury(rfc_num)
    root = rfc.find_root()
    root.gen_relation_html()
    root.gen_relation_html_with_les_miserables()