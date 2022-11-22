import os
import urllib.parse
import time
import PySimpleGUI as sg
import csv
#import numpy as np

#UI 機能統合など
from threading import Lock
#from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import tkinter as tk


import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver 
from Co_Shrimp import GoogleShrimp 
from Co_Spider import CoSpider 


thread_mode = ('noop','active','suspend','destroy')#意味ないかも
shrimp_stat = thread_mode[0]
spider_stat = thread_mode[0]

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
        [sg.Text('検索ワード :'), sg.Input(key='-SEARCH-SHRIMP-') , sg.Button('エビ',font=('',11)), sg.Button('suspend',font=('',11)), sg.Button('エビ終了',font=('',11))],
        [sg.Text('連続検索ワード :'), sg.Listbox ( search_word_list , size =(24 , 5) , key='-search-word-list-box-') , sg.Button('追加',font=('',11)),  sg.Button('削除',font=('',11)),sg.Button('リストの読み込み',font=('',11)), sg.Button('リストの保存',font=('',11))],
        [sg.Button('エビs',font=('',11)), sg.Button('suspend',font=('',11)), sg.Button('エビs終了',font=('',11))],
        [sg.Text('current :'),sg.Text('', key='-CURRENT-TEXT-SHRIMP-')],
        [ sg.Table (T , headings=H , auto_size_columns = False , vertical_scroll_only = False ,
            #def_col_width=32 ,
            col_widths=[45, 38],
            num_rows=9 ,
            display_row_numbers= True ,
            font =('',10) ,
            header_text_color= '#0000ff' ,
            header_background_color= '#cccccc',
            key='-TABLE-'
        )]

    ] , size=(base_frame_width, 320) 
    )

    frame2 = sg.Frame('',
    [
                [sg.Button('蜘蛛',font=('',12)), sg.Button('suspend',font=('',11)), sg.Button('蜘蛛終了',font=('',11)) , sg.Button('終了')],
                [sg.Text('', key='-ACT-')],                
                [sg.Listbox(values="", size=(120, 9), key='-LIST-', enable_events=True)]                
    ] , size=(base_frame_width, 180) 
    )

    frame3 = sg.Frame('',
    [
        [sg.Multiline(default_text='',size=(160,9), border_width=2, key='memo')]
    ] , size=(base_frame_width, 160) 
    )

    layout = [
                [frame1] , [frame2] 
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


    def shrimp_worker(search_word):
        coshrimp = GoogleShrimp(search_word=search_word , save_file_name="検索結果.csv" , breath = shrimp_breather)  
        coshrimp.boil()
        return 


    def shrimp_breather(switch , save_file_name="" , param_dic={}, current_text="") : # 戻り値 {}
        global shrimp_stat , search_result_all , go_on
        result = {}
        with __lock:    
            match switch:
                case "breath" :
                    result = {}
                    window['-CURRENT-TEXT-SHRIMP-'].update(current_text)
                case "life" :
                    result = {"life" : go_on}     
    
                case "clean_up" :
                    try:       
                        result = False
                        if param_dic :
                            search_result_all |= param_dic # kokokara 20221121
                            update_list = list()
                            for key_url , value_title in search_result_all.items():
                                update_list += [[value_title , key_url]]
                            window['-TABLE-'].update(update_list)# dic型の値からlist に変換して渡す必要がある　かそもそも集計してるそれを使うか

                            f_name = save_file_name
                            if not f_name :  
                                f_name = "nioh.csv"
                            f = open(f_name , mode="a" , newline="", encoding="UTF-8")     

                            writer = csv.writer(f)
                            
                            for row in update_list:
                                writer.writerow(row)
                            result = True    
                    finally:
                        f.close()
                        shrimp_stat = thread_mode[0]

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


    futures = []
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == '終了': # スレッドセーフで終了するように色々やってね
            break
        elif event == 'エビ':
            if shrimp_stat == 'noop' :
                s_str =  window['-SEARCH-SHRIMP-'].get()
                shrimp_executor = ThreadPoolExecutor(max_workers=1)
                shrimp_future = shrimp_executor.submit(shrimp_worker , s_str)
                shrimp_stat = thread_mode[1] #タプルとは
                go_on = True 
        elif event == 'suspend': # 停止する意味がないため、実装されない可能性高まる。癖でやってしまった
            if shrimp_stat == 'active' :
                
                shrimp_stat = thread_mode[2] # to suspend 
            if shrimp_stat == 'suspend' :
                
                shrimp_stat = thread_mode[1]  #back to active
        elif event == 'エビ終了':
            if shrimp_stat == 'active' or shrimp_stat == 'suspend' :
                go_on = False #発生したスレッドの処理を終了に促す
                shrimp_executor = None
                shrimp_stat = thread_mode[0]  #back to noop

        elif event == '追加':
            w = sg . PopupGetText ('検索ワード ' , title = '検索ワードリストへ追加')
            if w:
                search_word_list += [w + '\n']
                window ['-search-word-list-box-']. Update ( search_word_list )

        elif event == '削除':
            if values['-search-word-list-box-']:
                #ここにリストから選択して削除・アップデート
                search_word_list.remove(values['-search-word-list-box-'][0]) 
                window ['-search-word-list-box-'].Update( search_word_list )

        elif event == 'リストの読み込み':
            _search_word_load()
            window ['-search-word-list-box-'].Update( search_word_list )

        elif event == 'リストの保存':
            _search_word_save()
            window ['-search-word-list-box-'].Update( search_word_list )

        elif event == '-search-word-list-box-+-double click-':
            if values['-search-word-list-box-']:
                val = values['-search-word-list-box-'][0] 
                window ['-SEARCH-SHRIMP-'].Update(val)

        elif event == 'エビs':
            if shrimp_stat == 'noop' :



                shrimp_stat = thread_mode[1] 
                go_on = True 
             
        elif event == '蜘蛛':
            if 0 < len(search_result_all) :
                executor = ThreadPoolExecutor(max_workers=1)
                for name_url in search_result_all:
                    if 2 == len(name_url) :
                        futures.append(executor.submit(spider_worker, name_url[1]))

                #with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:   
                #    for name_url in search_result_all:
                #        if 2 == len(name_url) :
                #            futures.append(executor.submit(spider_worker, name_url[1]))

        elif event == '蜘蛛終了':
            window.refresh()

        elif event == '決定':#テストコード

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
    #ProcessPoolExecutor
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


