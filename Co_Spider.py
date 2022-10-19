from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import urlparse
from urllib.parse import urljoin
from os import makedirs
import os.path, time, re , csv

from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed
import random

from threading import Lock

from Arthropod_Base import Arthropod


import multiprocessing 
multiprocessing.set_start_method('spawn', True)

from logging import getLogger, StreamHandler, DEBUG 
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class CoSpider(Arthropod):
   #needless = "(twitter|instagram|facebook|youtube)"
   power_word = ["問い合" , "お問合"]
   positive_words = ["お名前","メールアドレス","フォーム","コンタクト","送信","問い合","件名" ,"お問合"
                     , "確認" , "進む" , "必須" , "タイトル" , "題名" , "本文" , "連絡先" , "フリガナ" , "内容"] 
   negative_words = ["レンタル","アカウント"] 

   ext = ".csv"
   test_files = {} # {[url] : bool}
   #detected_url = {} # {'title : str , ''url' : str , 'savepath' : str}
   detected = False

   enc = "UTF-8"
   init_error = False
   
   search_name = ""
   url = ""

   def __init__(self , sname , url = "",  breath = None , hedden_window = False) :# sname : 結果を保存するFILENAMEを指定している
      
      super().__init__(save_file_name=sname ,  breath = breath , hedden_window = hedden_window)
      
      #インスツール自体は先に済ませておくべき。
      #ここでは既に行われたアップデートのインストール先のパスが帰ってきている。
      self.search_name = sname
      self.url = url

      logger.debug("__init__ failure", url)
      return None


   def enum_links(self , html, base):# HTMLファイル内にあるlink 、a href　を拾い集める。result = list 
      soup = BeautifulSoup(html, "html.parser")
      links = soup.select("link[rel='stylesheet']")
      links += soup.select("a[href]")
      result = []

      for a in links:
         href = a.attrs['href']
         url = urljoin(base, href) 
         result.append(url)
      return result


   def __download_file_selenium(self , url): # result {'url' : str ,'savepath' : str ,  'isthis' bool}

      try:#ここをダウンロードからコンテンツチェックに変える
         result = {"url" : "" , "savepath" : "" ,  "isthis" : False , "needless" : False}
         o = urlparse(url)

         result["url"] = url 
         #savepath 
         savepath = self.save_directory + "/" + o.netloc + o.path + o.query
         if re.search(r"/$", savepath):#末尾に / が無いからと言ってディレクトリとは限らない。
            savepath += "index.html"

         result["savepath"] = savepath

         if re.search(self.needless , savepath):
            result["needless"] = True
            return result #savepath

         savedir = os.path.dirname(savepath)

         if os.path.exists(savepath): 
            return result

         logger.debug("get=" + url)
         self.driver.get(url)#直後のデータとURLが有効

         time.sleep(1+random.uniform(2, 2))
         t_len = len(self.driver.page_source)
         t_url = self.driver.current_url

         if "title" not in self.detected_url.keys(): #最初のページのタイトルだけを得る
            self.detected_url = {"title" : self.driver.title} 
         #問い合わせフォームであるかをテストするコードを入れる場所
         res = self.target_form_detector(self.driver.page_source)   # result {"t" : int , "p" : int , "n" : int} / None
         if (2 <= res["p"])and(1 <= res["t"]) :
         #p , t  それぞれの値から評価　フローを変える
         #コンタクトフォームと思しきHTMLは保存しておくべき 解析用サンプル（基本保存するのはこれだけでよい
            result["isthis"] = True
            self.detected = True

            o = urlparse(t_url)
            savepath = self.save_directory + "/" + o.netloc + o.path + o.query
            if re.search(r"/$", savepath):#末尾に / が無いからと言ってディレクトリとは限らない。
               if 0 <= t_len :
                  savepath += "index.html"
            else:
               if 0 <= t_len :# コンテンツあり。ディレクトリではない。
                  if not re.search(r".(html|htm|cgi)$", savepath):# ここにファイル名が無ければ
                     savepath += "/index.html"  
               else:
                  savepath += "/"

            savedir = os.path.dirname(savepath)
            result["savepath"] = savepath

            self.detected_url |= {"url" : url}

            if os.path.exists(savepath): 
               return savepath

         if not os.path.exists(savedir):
            print("mkdir=", savedir)
            os.makedirs(savedir) #日本語でディレクトリ名を作成できない
      
         w_str = self.driver.page_source
         with open(savepath, mode="w", encoding=self.enc) as f: #保存するためにエンコードを先んじて取得しておくべき
            f.write(w_str)
            f.close
           
         time.sleep(1+random.uniform(2, 2))
         return result

      except:
         logger.debug("ダウンロード失敗:" + url)
         return None


   def target_form_detector(self,html):#コンタクトフォームであるか調べる  result {"t" : int "p" : int , "n" : int}
      #<form タグの位置から走査をスタートさせ /form>かデータ末尾に内にある各文字列を評価させる。
      #<title> タグから power_word を探す <title>タグは複数存在する場合がある
      result = {"t" : 0 , "p" : 0 , "n" : 0}
      t_len = len(html) # 末尾
      if 0 == t_len :
         return result      
      low_html = html.lower()   
      t_cnt = 0 ; p_cnt = 0 ; n_cnt = 0 

      def scan(b_tag , e_tag , words):
         nonlocal low_html , t_len

         result = 0 
         t_f_b_idx = low_html.find(b_tag) # 最初の位置
         t_f_e_idx = low_html.find(e_tag) 

         while -1 != t_f_b_idx :
            t_f_b_idx = low_html.find(b_tag , t_f_b_idx ) 
            if -1 != t_f_b_idx :
               t_f_e_idx = low_html.find(e_tag , t_f_b_idx ) 
               if -1 ==  t_f_e_idx :
                  t_f_e_idx = t_len
               #繰り返される別の処理
               for target_str in  words:
                  if -1 != t_f_b_idx :
                     t_pos = html.find(target_str , t_f_b_idx , t_f_e_idx)
                     if -1 != t_pos :
                        result += 1
                         
               t_f_b_idx = t_f_e_idx
         return result

      t_cnt = scan("<title","/title>",self.power_word ) 
      p_cnt = scan("<form","/form>",self.positive_words )
      n_cnt = scan("<form","/form>",self.negative_words )

      result = {"t" : t_cnt , "p" : p_cnt , "n" : n_cnt}
      return result


   def __download_file(self , url):  #URL次第ではパスが作れずエラーを吐く
   #Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36

      try:#ここをダウンロードからコンテンツチェックに変える
         print("download=", url)
         #urlretrieve(url, savepath)
         user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
         req = urllib.request.Request(url, headers={'User-Agent': user_agent}, method='GET')
         with urllib.request.urlopen(req) as response:
            print(response.getcode())
            print(response.info())
            t_url = response.geturl()
            t_len = response.length
            o = urlparse(t_url)

            savepath = "./" + o.netloc + o.path
            if re.search(r"/$", savepath):#末尾に / が無いからと言ってディレクトリとは限らない。
               savepath += "index.html"
            else:
               if 0 <= t_len :# コンテンツあり。ディレクトリではない。
                  savepath += "/index.html"
            savedir = os.path.dirname(savepath)

            if os.path.exists(savepath): 
               return savepath

            if not os.path.exists(savedir):
               print("mkdir=", savedir)
               os.makedirs(savedir) #日本語でディレクトリ名を作成できない→出来た
            #data = urllib.request.urlopen(url).read()
            with open(savepath, mode="wb") as f:
               f.write(response.read())
            #   print(response.read().decode(), file=save_file)
         time.sleep(1+random.uniform(1, 2))
         return savepath
      except urllib.error.HTTPError as e:
         print(e)
         print(e.code)
         print(e.reason)
      except urllib.error.URLError as e:
         print(e)
         print(e.code)
         print(e.reason)

      except:
         print("ダウンロード失敗:", url)
         return None


   def finish_it(self) -> bool :
      result = False
      if not self.url :
         return result
      o = urlparse(self.url)
      hostname = o.hostname

      r_result = self.recursive_async(self.url , self.url) # 結果が何であれ記録が必要
      if r_result : # 結果の保存はここで
         self.detected_url |= {"hostname" : hostname}
         result = True 
         self.save_to_csv_a()  
      else:
         self.browser_close()

      return result


   def recursive_async(self , url, root_url):
      
      nest = 0
      result = False

      r_selenium = self.__download_file_selenium(url)  #ドメインであるはずであるため

      if True == r_selenium["needless"] : return result #不要なURLである印がある
      savepath = r_selenium["savepath"] 
      if savepath is None: return result
      if savepath in self.test_files: return result # 既に辞書にあるURLである
      if self.detected : return result

      self.test_files[savepath] = True
      logger.debug("recursiv_sync=", url)

      #encodingは各サイトで幾つか試す必要があるだろう  
      try :
         html = open(savepath, "r", encoding="UTF-8").read()  #ワードプレスはこれ
         self.enc="UTF-8"   #一切効いてない
      except :
         try :
            html = open(savepath, "r", encoding="CP932").read()  #今のところそれ以外
            self.enc="CP932"
         except :
            try :
               html = open(savepath, "r", encoding="shift_jis").read()  #今のところそれ以外
               self.enc="shift_jis"
            except :

               return "対策求" # まだ先はあろう

      links = self.enum_links(html, url)
      for link_url in links:   # self.detectedが来るまではURLをひたすら走査しなくなった時点で終わる。この辺に強制終了を置ける。
         if link_url.find(root_url) != 0: 
            if link_url.find(self.lucky_urls[1]) == 0:        #限定的ドメインは通過させるよう組まねばならない
               continue  
            
         if re.search(r".(css|css2)", link_url): continue
         if re.search(r".(html|htm|cgi)$", link_url):
            if self.detected : break  
            ++nest
            if 2 > nest :
               self.recursive_async(link_url, root_url)   # ネストのチェック

            --nest   
            continue

         l_result = self.breather("life") 
         if not l_result["life"]: break
         if self.detected : break

         self.__download_file_selenium(link_url)
 
      return self.detected


   #def save_to_csv_a(self) : # 書き込むのは一行のみ

   #   super().save_file_name()
   #   data_list = [self.detected_url["title"] , self.detected_url["hostname"] , self.detected_url["url"] , str(id(self)) , str(id(self.driver))]        
   #   result = self.breath("save" , data_list) 
      #戻り値の検証

   #   return result


   def get_result_list(self) -> list:
      result = list()
      if not self.detected :
         return result
      result = [self.detected_url["title"] , self.detected_url["hostname"] , self.detected_url["url"], str(id(self)) , str(id(self.driver))]  

      return result


#CoSpider end


#開発用

__lock = Lock()
go_on = True
def initializer(string):
        print(f'{string} init thread!')


def worker(url): 
        # with open(filename) as file: data = file.read()
        #data = filename
        #sleep(filenames[data]) # heavy task !

    cs = CoSpider("nioh" , url=url , breath=breather ) 
    cs.finish_it()
    #return f"started"
    return cs.get_result_list()



def breather(switch , save_file_name="" , param_list=list()) : # 戻り値 {}   デバッグ用、オリジナルはskyllaに
    result = {}
    with __lock:    
        match switch:
            case "breath" :
                result = {}

            case "life" :
                result = {"life" : go_on}   

            case "save" :
                try:       
                    f_name = save_file_name
                    if not f_name :  
                        f_name = "eldenring.csv"
                    f = open(f_name , mode="a" , newline="", encoding="UTF-8")       
                    for a_list in param_list :
                        writer = csv.writer(f)
                        writer.writerow(a_list)
                finally:
                    f.close()

                result = {}

    return result

if __name__ == "__main__": #開発用
   import multiprocessing 
   multiprocessing.set_start_method('spawn', True)
     
   

   u0 = "https://forms.gle/DLUDB7GZ7V1Q9Ddc9" #謎のエラー

   u1 = "https://atsuma-note.jp/"
   u2 = "https://bonten.cc/"
   u3 = "https://akubi-office.com/"
   u4 = 'https://kokusai-bs.jp/' 
   u5 = "https://exceed-confect.co.jp/"
   u6 = "https://music.oricon.co.jp"


   target_list = [u0 , u1, u2, u3, u4 ,u5 , u6]

   with ProcessPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:
      futures = []
            #for filename in filenames.keys():
            #    futures.append(executor.submit(worker, filename))
      for url in target_list:
         futures.append(executor.submit(worker, url))

  

   #for url in target_list :
   #   cs = CoSpider("nioh" , url) 
   #   cs.finish_it()


   
