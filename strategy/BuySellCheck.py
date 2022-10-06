import numpy as np
import pandas as pd
import time

class BuySellCheck:

    def __init__(self, kiwoom_class_param, stock_class_param):
        self.st_class = stock_class_param
        self.kw_class = kiwoom_class_param

        self.position = self.kw_class.position
        self.deposit = self.kw_class.deposit


    def buy_sell_check(self):
        for idx, code in enumerate(self.st_class.getUniverse().keys()):
            print("매수/매도 로직 체크 >> {}/{} : {}/{}".format(idx, len(self.st_class.getUniverse()), code, self.st_class.getUniverse()[code]["code_name"]))

            if code in self.kw_class.universe_realtime_transaction_info.keys():
                print(self.kw_class.universe_realtime_transaction_info[code])

            # (1) 접수한 주문이 존재하는지 확인
            if code in self.kw_class.order.keys():
                print("주문한 내역이 존재합니다.", self.kw_class.order[code])

                # (2) 주문 접수하고 체결이 모두 완료되었는지 확인
                if self.kw_class.order[code]['미체결수량'] == 0:
                    # (2-1) 미체결수량이 0이고 현재 보유한 종목이라면 "매수"가 완료된 것
                    if code in self.position.keys():
                        print("매수 완료되어 보유 중인 종목입니다", self.position[code])
                        # (2-2) 보유 중이니 매도 로직 실행
                        if self.check_sell_signal(code):
                            self.order_sell(code)
                    # (2-3) 미체결수량이 0인데 보유한 종목이 아니라면, "매도"를 완료한 것일테니 다시 매수 타점있는지 확인
                    else:
                        self.check_buy_signal_and_order(code)
                        pass

                # (2-4) 주문 접수하고 부분체결 혹은 아직 체결되지 않은 경우
                else:
                    print("아직 미체결 수량이 남아 있으므로 체결 되기 까지 기다립니다.")

            # (3) 접수한 주문이 없다면, 보유종목인지 확인
            elif code in self.position.keys():
                print("보유 종목입니다.", self.position[code])
                # (3-1) 매도 조건에 부합하는지 확인
                if self.check_sell_signal(code):
                    # (3-2) 매도 대상이면 매도 주문 접수!
                    self.order_sell(code)

            # (4) 접수 주문도 없고 보유종목도 아니라면 매수 대상인지 확인 후 주문 접수!
            else:
                print("접수된 주문도 없고 보유 종목도 아니므로 매수 대상인지 체크합니다.")
                self.check_buy_signal_and_order(code)
                pass

            time.sleep(1)


    def check_sell_signal(self, code):
        universe_item = self.st_class.getUniverse()[code]
        # print(universe_item)
        # print(universe_item.keys())

        if code not in self.kw_class.universe_realtime_transaction_info.keys():
            print("매도 대상 확인 과정에서 아직 체결정보가 없습니다.")
            return

        df = universe_item["price_df"].copy()


        # 종가(close) 기준으로 이동평균 구하기. 5일이 아니라 다른 값을 원하면 window 값을 변경
        # df['ma5'] = df['close'].rolling(window=5, min_periods=1).mean()
        #
        # # RSI(N) 계산하기.
        # period = 14
        # date_index = df.index.astype('str')
        # U = np.where(df['close'].diff(1) > 0, df['close'].diff(1), 0)
        # D = np.where(df['close'].diff(1) < 0, df['close'].diff(1) * (-1), 0)
        # AU = pd.DataFrame(U, index=date_index).rolling(window=period).mean()
        # AD = pd.DataFrame(D, index=date_index).rolling(window=period).mean()
        # RSI = AU / (AU + AD) * 100
        # df['RSI(14)'] = RSI

        # 보유종목의 매입가 구하기.
        purchase_price = self.position[code]['매입가']

        # 보유종목의 현재가 구하기.
        close = self.position[code]['현재가']

        # 보유종목의 수익률 구하기.
        profit = self.position[code]['수익률']

        # df[:-1]은 제일 마지막 행을 의미함. 가장 최근의 ma5, RSI(14) 구하기.
        # rsi = df[:-1]['ma5'].values[0]
        # ma5 = df[:-1]['RSI(14)'].values[0]

        # print("code:{} / rsi signal:{}(잠시제외) / profit signal:{}".format(code, rsi > 80, close > purchase_price * 1.0233))

        if close > purchase_price * 1.0233:  # 익절
            print("익절 조건에 해당됩니다.")
            print("매입가:{} / 현재가:{} / 수익률:{}".format(purchase_price, close, profit))
            return True
        elif close < purchase_price * 0.98:  # 손절
            print("손절 조건에 해당됩니다.")
            print("매입가:{} / 현재가:{} / 손절율:{}".format(purchase_price, close, profit))
            return True
        else:
            print("매도 조건을 만족하지 않아 매도를 보류합니다.")
            return False

    def order_sell(self, code):
        # 종목명을 가져옴 >> 추후에 메시징과 연동할때 필요해서 갖고옴.
        universe_item = self.st_class.getUniverse()[code]
        code_name = universe_item['code_name']

        # 보유수량을 확인 함
        quantity = self.position[code]['보유수량']
        print(quantity)

        # 최우선 매도호가를 확인 함
        ask = self.kw_class.universe_realtime_transaction_info[code]['(최우선)매도호가']
        print(ask)

        # 매도 주문 접수!
        order_result = self.kw_class.send_order('send_sell_order', '1001', 2, code, quantity, ask, '00')
        print("매도 주문을 접수합니다! :", order_result)

    def check_buy_signal_and_order(self, code):
        universe_item = self.st_class.getUniverse()[code]
        code_name = universe_item['code_name']

        # 현재 체결정보가 존재하지 않는지를 확인.
        if code not in self.kw_class.universe_realtime_transaction_info.keys():
            print("매수 대상 확인 과정에서 아직 체결정보가 없습니다.")
            return

        # 1분봉 가격데이터 밸류를 복사해서 df 변수에 담음
        df = universe_item['price_df'].copy()

        # 이동평균값 구해서 새로운 열로 추가
        df['ma120'] = df['close'].rolling(window=120, min_periods=1).mean()
        ma120 = df[-1:]['ma120'].values[0]

        # 현재가
        close = self.kw_class.universe_realtime_transaction_info[code]['현재가']

        # 2차 거름망
        if (df['VM'].max() > 140 and df['high'].max() >= df['open'][0] * 1.09) or (df['VM'].max() > 90 and df['high'].max() >= df['open'][0] * 1.15) == False:
            return
        # 추가 거름망
        if ma120 > close:
            return

        # RSI 구해서 새로운 열로 추가
        # period = 14
        # date_index = df.index.astype("str")
        # U = np.where(df['close'].diff(1) > 0, df['close'].diff(1), 0)
        # D = np.where(df['close'].diff(1) < 0, df['close'].diff(1) * (-1), 0)
        # AU = pd.DataFrame(U, index=date_index).rolling(window=period).mean()
        # AD = pd.DataFrame(D, index=date_index).rolling(window=period).mean()
        # RSI = AU / (AU + AD) * 100
        # df['RSI(14)'] = RSI

        # df[-1:]은 제일 마지막 행을 의미함. 가장 최근 데이터 기준 잡음.
        # rsi = df[-1:]['RSI(14)'].values[0]
        # ma20 = df[-1:]['ma20'].values[0]
        # print("code_name:{} / signal1:{} / signal2:{}".format(code_name, close > ma20 > ma60, rsi <= 50))

        # 양수인 빈덱스값만 따로 dataframe 생성
        df1 = df.loc[(df['Vindex'] > 0), ['date', 'Vindex']]

        # 1타점 거래 (이전 계단)
        for i in range(2, len(df1.index) + 1):
            if (((int(df1.iloc[-1]['date'])) - int(df1.iloc[-i]['date'])) > 400) and int(df1.iloc[-1]['Vindex']) >= int(df1.iloc[-i]['Vindex']) * 1.03:
                if close == (int(df1.iloc[-i]['Vindex']) * 1.005):
                    budget = round(int(self.deposit) / 100)
                    bid = self.kw_class.universe_realtime_transaction_info[code]['(최우선)매수호가']
                    quantity = round(budget / bid)
                break
            else:
                continue
        # 2타점 거래 (현재 계단)
        if df['close'].max() >= int(df1.iloc[-1]['Vindex'])* 1.06:
            if close == (int(df1.iloc[-1]['Vindex']) * 1.005):
                budget = round(int(self.deposit) / 100)
                bid = self.kw_class.universe_realtime_transaction_info[code]['(최우선)매수호가']
                quantity = round(budget / bid)
        # elif df['close'].max() >= int(df1.iloc[-1]['Vindex'])* 1.06:

        # 3타점 거래 (VI)
        if df['VM'].max() > 140 and  df['open'][0] * 1.12 <= df['close'].max() <= df['open'][0] * 1.14:
            if close == df['open'][0] * 1.1005:
                budget = round(int(self.deposit) / 100)
                bid = self.kw_class.universe_realtime_transaction_info[code]['(최우선)매수호가']
                quantity = round(budget / bid)



        # 매수 신호 확인! (매수 조건에 부합한다면 다음 코드로 넘어감)
        # if close > ma20 > ma60 and rsi <= 50:
        #     budget = round(int(self.deposit) / 100)
        #     bid = self.kw_class.universe_realtime_transaction_info[code]['(최우선)매수호가']
        #     quantity = round(budget / bid)
        # 매수신호에 해당되지 않으면 그대로 함수 종료.
        # else:
        #     print("매수 신호 조건을 만족하지 않습니다.")
        #     return

        # 주문 수량이 1미만이거나 예수금이 0보다 같거나 작으면 그대로 함수 종료.
        if quantity < 1 or int(self.deposit) <= 0:
            print("주문 수량이 1 미만이거나 예수금이 부족해서 주문 불가합니다.")
            return

        print("예수금:{}원 / 매수한도금액:{}원 / 매수수량:{}주".format(int(self.deposit), budget, quantity))

        # 매수 주문 접수!
        order_result = self.kw_class.send_order('send_buy_order', '1001', 1, code, quantity, bid, '00')
        print("매수 주문을 접수합니다! : ", order_result)