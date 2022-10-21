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
search_result_all = [[]]

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

    frame1 = sg.Frame('',
    [
        [sg.Text('検索ワード :'), sg.Input(key='-SEARCH-SHRIMP-') , sg.Button('エビ',font=('',11)), sg.Button('suspend',font=('',11)), sg.Button('エビ終了',font=('',11))],
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

    ] , size=(base_frame_width, 180) 
    )

    frame2 = sg.Frame('',
    [
                [sg.Button('蜘蛛',font=('',12)), sg.Button('suspend',font=('',11)), sg.Button('蜘蛛終了',font=('',11)) , sg.Button('終了')],
                [sg.Text('', key='-ACT-')],                
                [sg.Listbox(values="", size=(120, 9), key='-LIST-', enable_events=True)]                
    ] , size=(base_frame_width, 220) 
    )

    frame3 = sg.Frame('',
    [
        [sg.Multiline(default_text='',size=(160,9), border_width=2, key='memo')]
    ] , size=(base_frame_width, 160) 
    )

    layout = [
                [frame1] , [frame2] , [frame3]
            ]

    window = sg.Window('ui_sample_skylli', layout)


    def shrimp_worker(search_word):
        coshrimp = GoogleShrimp(search_word=search_word , save_file_name="検索結果.csv" , breath = shrimp_breather)  
        coshrimp.boil()
        return 


    def shrimp_breather(switch , save_file_name="" , param_list=list(), current_text="") : # 戻り値 {}
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
                        if param_list :
                            search_result_all.extend(param_list)
                            window['-TABLE-'].update(param_list)

                            f_name = save_file_name
                            if not f_name :  
                                f_name = "nioh.csv"
                            f = open(f_name , mode="a" , newline="", encoding="UTF-8")     

                            writer = csv.writer(f)
                            
                            for row in param_list:
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

        elif event == '蜘蛛':
            if 0 < len(search_result_all) :
                with ThreadPoolExecutor(max_workers=3, initializer=initializer, initargs=('pool',)) as executor:   
                    for name_url in search_result_all:
                        if 2 == len(name_url) :
                            futures.append(executor.submit(spider_worker, name_url[1]))

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


