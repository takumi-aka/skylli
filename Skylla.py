import os
import urllib.parse
import time
import PySimpleGUI as sg
import csv
#import numpy as np

#UI 機能統合など
from threading import Lock
#from concurrent.futures.process import ProcessPoolExecutor
import concurrent
from concurrent.futures import ThreadPoolExecutor

import tkinter as tk


import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver 
from Co_Shrimp import GoogleShrimp 
from Co_Spider import CoSpider 


worker_thread_with = None
thread_mode = {'noop' : 0 ,'active' : 1 , 'destroy' : 2 } 
shrimp_stat = thread_mode['noop']
spider_stat = thread_mode['noop']

#coshrimp  #検索エンジンからデータをあさるクラス
#cospider  #各サイトにコンタクトフォームが存在するか走査するクラス

shrimp_executor = None #coshrimp実行の為のサブスレッド

__lock = Lock() #クリティカルセクション
go_on = True
search_result_all = {}

def initializer(string):
    print(f'{string} init thread!')


def update_chrome_install() :
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    webdriver.Chrome(ChromeDriverManager().install(), options=options)
    webdriver.Chrome.close
    return


if __name__ == '__main__':

    import multiprocessing 

    multiprocessing.set_start_method('spawn', True)
    update_chrome_install() 
    
    sg.theme('DarkBlue11')

    T = [[]]
    H = ['Title','URL']

    base_frame_width = 720
    search_word_list = []
    frame1 = sg.Frame('',
    [
        [sg.Text('検索ワード :'), sg.Input(key='-SEARCH-SHRIMP-') , sg.Button('エビ',font=('',11)),  sg.Button('エビ終了',font=('',11))],
        [sg.Text('連続検索ワード :'), sg.Listbox ( search_word_list , size =(24 , 5) , key='-search-word-list-box-') , sg.Button('追加',font=('',11)),  sg.Button('削除',font=('',11)),sg.Button('リストの読み込み',font=('',11)), sg.Button('リストの保存',font=('',11))],
        [sg.Button('エビs',font=('',11)), sg.Button('エビs終了',font=('',11))],
        [sg.Text('passing :'),sg.Text('', key='-CURRENT-TEXT-SHRIMP-')],
        [ sg.Table (T , headings=H , auto_size_columns = False , vertical_scroll_only = False ,
            #def_col_width=32 ,
            col_widths=[45, 38],
            num_rows=9 ,
            display_row_numbers= True ,
            font =('',10) ,
            header_text_color= '#0000ff' ,
            header_background_color= '#cccccc',
            key='-TABLE-'
        )],
        [sg.Button('CSVを読み込む',font=('',11)), sg.Button('CSVへ保存',font=('',11))]
    ] , size=(base_frame_width, 376) 
    )

    frame2 = sg.Frame('',
    [
        [sg.Text('狭間のインスタンス : ')] , [sg.Text('', key='-STAT2-')] , [sg.Text('', key='-STAT1-')] , [sg.Text('', key='-STAT-')]
    ] , size=(base_frame_width, 32) 
    )

    frame3 = sg.Frame('',
    [
                [sg.Button('蜘蛛',font=('',12)),  sg.Button('蜘蛛終了',font=('',11)) , sg.Button('終了')],
                [sg.Text('', key='-ACT-')],                
                [sg.Listbox(values="", size=(120, 9), key='-LIST-', enable_events=True)]                
    ] , size=(base_frame_width, 220) 
    )



    layout = [
                [frame1] , [frame2] ,[frame3] 
            ]

    window = sg.Window('ui_sample_skylli', layout , resizable=True,  finalize=True)
    window["-search-word-list-box-"].bind('<Double-Button-1>' , "+-double click-")  #-Button

    def _search_word_load() :#ファイルからロード
        global search_word_list

        fTyp = [("検索ワードリスト", "*.txt")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.askopenfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):
            f = open(file_name.name , mode="r" , encoding="UTF-8")     
            search_word_list = [] 
            data = f.read()
            for line in data.splitlines():
                search_word_list += [line + '\n']
            f.close()  
            window ['-search-word-list-box-'].Update( search_word_list )
        return

    def _search_word_save() :#ファイルへセーブ
        global search_word_list

        fTyp = [("検索ワードリスト", "*.txt")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.asksaveasfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):
            f = open(file_name.name , mode="w+" , encoding="UTF-8")     
            f.writelines([row for row in search_word_list]) 
            f.close()            

        return

    def _csv_load() :
        global search_result_all

        fTyp = [("CSVファイル", "*.csv")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.askopenfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):
            f = open(file_name.name , mode="r" ,newline='', encoding="UTF-8")     
            csvreader = csv.reader(f)
            if csvreader :
                search_result_all = {}
                update_list = list()
                for row in csvreader:
                    search_result_all |= {row[1] : row[0]}
                    update_list += [row]
            f.close()  
            window['-TABLE-'].update(update_list)
        return

    def _csv_save() :
        global search_result_all

        if not search_result_all :
            return

        fTyp = [("CSVファイル", "*.csv")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.asksaveasfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):

            f = open(file_name.name , mode="w+" , newline="" , encoding="UTF-8")     
            writer = csv.writer(f)
                            
            update_list = list()
            for key_url , value_title in search_result_all.items():
                update_list += [[value_title , key_url]]

            for row in update_list:
                writer.writerow(row)

            f.close()            

        return

    def shrimp_worker(search_word):
        coshrimp = GoogleShrimp(search_word=search_word , save_file_name="検索結果.csv" , breath = shrimp_breather) 
        return coshrimp.boil()

    def shrimp_breather(switch , save_file_name="" , param_dic={}, current_text="") : # 戻り値 {}
        global shrimp_stat , search_result_all , go_on
        result = {}
        with __lock:    
            match switch:
                case "breath" :
                    result = {}
                    window['-CURRENT-TEXT-SHRIMP-'].update(current_text)
                case "life" :
                    result = {'life' : go_on}     
    
                case "clean_up" :
                    try:       
                        result = {"clean_up" : False}
                        if param_dic :
                            search_result_all |= param_dic # kokokara 20221121
                            update_list = list()
                            for key_url , value_title in param_dic.items():#その検索ワードの成果だけを表示させたいためparam_dicにしてある
                                update_list += [[value_title , key_url]]

                            window['-TABLE-'].update(update_list)

                            f_name = save_file_name
                            if not f_name :  
                                f_name = "nioh.csv"
                            f = open(f_name , mode="a" , newline="", encoding="UTF-8")     

                            writer = csv.writer(f)
                            
                            for row in update_list:
                                writer.writerow(row)
                            result = {"clean_up" : True}    
                    finally:
                        f.close()
                        shrimp_stat = thread_mode['noop']

        return result



    def spider_worker(url=""):
        cospider = CoSpider("nioh" , url=url , breath=spider_breather , hedden_window=False) 
        cospider.finish_it()
        return cospider.get_result_list()


    def spider_breather(switch , save_file_name="" , param_list=list(), current_text="") : # 戻り値 {}
        global shrimp_stat , search_result_all , go_on
        result = {}
        with __lock:    
            match switch:
                case "breath" :
                    result = {}
                    #window['-CURRENT-TEXT-'].update(current_text)
                case "life" :
                    result = {"life" : go_on}   
    
                case "clean_up" :
                    try:       
                        result = False
                        if param_list :

                            f_name = save_file_name
                            if not f_name :  
                                f_name = "eldenring"
                            f = open(f_name + ".csv" , mode="a" , newline="", encoding="UTF-8")                       
                            if param_list :    
                                writer = csv.writer(f)                
                                writer.writerow(param_list)

                            result = True    
                    finally:
                        f.close()
                        shrimp_stat = thread_mode[0]

        return result



    def skylli_worker_thread_with(swt , param):#ワーカースレッドが終わるまで待ってるスレッド  状態遷移の主軸に
        global worker_thread_with
        if None == worker_thread_with :
            return 

        match swt:

            case "swt_shrimp" : 
                with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor: 
                    futures.append(executor.submit(shrimp_worker, param)) #stringなのかチェックしてない
                    for future in concurrent.futures.as_completed(futures):# キューではない
                        result = future.result() 

            case "swt_shrimps" : 
                with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:   
                    for search_word in param:#listなのかチェックしていない
                        futures.append(executor.submit(shrimp_worker, search_word))

                    for future in concurrent.futures.as_completed(futures):
                        result = future.result() #正常終了か問題ありか位は乗せておきたい


            case "swt_spider" : 
                with ThreadPoolExecutor(max_workers=4, initializer=initializer, initargs=('pool',)) as executor:   
                    for url in param:#listなのかチェックしていない
                        futures.append(executor.submit(spider_worker, url))

                    for future in concurrent.futures.as_completed(futures):
                        result = future.result() #正常終了か問題ありか位は乗せておきたい

        worker_thread_with = None
        return 


    futures = []
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == '終了': # スレッドセーフで終了するように main(any time)
            break

        elif event == 'エビs':#subthread
            if (shrimp_stat == thread_mode['noop']) and (0 < len(search_word_list)) and (None == worker_thread_with) :
                executor = ThreadPoolExecutor(max_workers=1)
                shrimp_stat = thread_mode['active'] 
                go_on = True                 
                worker_thread_with = executor.submit(skylli_worker_thread_with , 'swt_shrimps' , search_word_list)
             
        elif event == '蜘蛛':#subthread   # list からdic に代わってるので動作不可 
            if (0 < len(search_result_all)) and (None == worker_thread_with) :
                executor = ThreadPoolExecutor(max_workers=1)
                url_list = list() 
                for url in search_result_all.keys() :
                    url_list += [url]
                if url_list:
                    shrimp_stat = thread_mode['active'] 
                    go_on = True 
                    worker_thread_with = executor.submit(skylli_worker_thread_with , 'swt_spider' , url_list)

        elif event == 'エビ': #subthread
            if (shrimp_stat == thread_mode['noop'] )  and (None == worker_thread_with) :
                s_str =  window['-SEARCH-SHRIMP-'].get()
                if s_str : #スペースだろうが検索するよ 正規化はしない
                    executor = ThreadPoolExecutor(max_workers=1)
                    shrimp_stat = thread_mode['active'] 
                    go_on = True                     
                    worker_thread_with = executor.submit(skylli_worker_thread_with , 'swt_shrimp' , s_str)

                
        elif event == 'エビ終了': #main(any time)
            if shrimp_stat == thread_mode['active'] :
                go_on = False #発生したスレッドの処理を終了に促す
                shrimp_executor = None
                shrimp_stat = thread_mode['noop']  #back to noop

        elif event == '追加': #main(any time)
            w = sg . PopupGetText ('検索ワード ' , title = '検索ワードリストへ追加')
            if w:
                search_word_list += [w + '\n']
                window ['-search-word-list-box-']. Update ( search_word_list )

        elif event == '削除': #main(any time)
            if values['-search-word-list-box-']:
                search_word_list.remove(values['-search-word-list-box-'][0]) 
                window ['-search-word-list-box-'].Update( search_word_list )

        elif event == 'リストの読み込み': #main(any time)
            _search_word_load()
            window ['-search-word-list-box-'].Update( search_word_list )

        elif event == 'リストの保存': #main(any time)
            _search_word_save()

        elif event == 'CSVを読み込む': #main(any time)
            _csv_load()

        elif event == 'CSVへ保存': #main(any time)
            _csv_save()




        elif event == '-search-word-list-box-+-double click-': #main(any time)
            if values['-search-word-list-box-']:
                val = values['-search-word-list-box-'][0] 
                window ['-SEARCH-SHRIMP-'].Update(val)


        elif event == '蜘蛛終了': #main(any time)
            window.refresh()

        elif event == '決定':

            sg.Multiline.Update()   


    window.close()


    exit()
    
    #Co_spider テスト
    u0 = "https://wx10.wadax.ne.jp/~yoshidakaya-co-jp/" 
    #url = "https://www.octoparse.jp/"
    u1 = "https://oec-evaluation.uh-oh.jp/"
    u2 = "https://bonten.cc/"
    u3 = "https://akubi-office.com/"
    u4 = 'https://kokusai-bs.jp/' 
    u5 = "https://exceed-confect.co.jp/"

    target_list = [u0 , u2, u3, u3, u4 ,u5]

    futures = []

    #ProcessPoolExecutor   破棄
    with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:       

        for url in target_list:
            futures.append(executor.submit(worker, url))

        #for future in as_completed(futures):
        #    r_list = list(future.result()) 


        if futures :
            try:       
                f = open("nioh" + ".csv" , mode="a" , newline="", encoding="UTF-8")           
                for ft in futures :
                    r_list = list(ft.result())
                    if r_list :
                    # 排他的になってない 
                        writer = csv.writer(f)
                        writer.writerow(r_list)
            finally:
                f.close()

        #sg.theme_previewer()


