"""Existing adapters and optional dependencies only; never imports a crawler/model."""
import importlib.util,sys
REQUIRES={'api':[],'html':['bs4'],'wordpress_listing':['bs4','crawl4ai','lxml']}
def modules():
 result={}
 for name in ['bs4','crawl4ai','lxml']:
  try:result[name]=importlib.util.find_spec(name)is not None
  except (ImportError,ValueError,AttributeError):result[name]=False
 return result
def missing(kind,available=None):
 available=modules()if available is None else available
 return [name for name in REQUIRES[kind]if not available.get(name,False)]
def describe():
 found=modules();version=sys.version_info>=(3,10)
 return {'modules':found,'api':version,'html':version and not missing('html',found),'wordpress_listing':version and not missing('wordpress_listing',found),'requirements':REQUIRES,'runtime_imports_tested':False,'network_tested':False}
