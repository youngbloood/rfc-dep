#!/usr/bin/python3
import json
import simplejson
from pyecharts import options as opts
from pyecharts.charts import Graph
import sys
import re
from typing import Union
import requests

debug = False
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
        root_rfc = None
        while True:
            _root_rfc = min_rfc(updates_rfc)
            if root_rfc is None:
                root_rfc = _root_rfc
            elif root_rfc == _root_rfc:
                break
            updates_rfc = _root_rfc.update_rfcs
        return root_rfc

    def gen_relation_html(self):
        nodes = []
        links = []

        c = (
            Graph()
            .add("", nodes, links, repulsion=4000)
            .set_global_opts(title_opts=opts.TitleOpts(title="Graph-GraphNode-GraphLink"))
            .render("graph_with_options.html")
        )
        
        


def deep_qeury(rfc_num: str, m: dict={}):
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
        rfc.updated_by_rfc.append(deep_qeury(name,m))
    
    for name in rfc.updates:
        if name in m.keys():
            rfc.updates_rfc.append(m[name])
            continue
        rfc.updates_rfc.append(deep_qeury(name,m))

    for name in rfc.obsoletes_by:
        if name in m.keys():
            rfc.obsoletes_by_rfc.append(m[name])
            continue
        rfc.obsoletes_by_rfc.append(deep_qeury(name,m))

    for name in rfc.obsoletes:
        if name in m.keys():
            rfc.obsoletes_rfc.append(m[name])
            continue
        rfc.obsoletes_rfc.append(deep_qeury(name,m))

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