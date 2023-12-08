import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import time
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

#read anything from a csv format
closed = pd.read_csv('data/closed.csv')
closed=closed.dropna(axis=1)
opened = pd.read_csv('data/opening.csv')

st.set_page_config(
    page_title = "Real-time data Dashboard",
    page_icon = "💵",
    layout = "wide"
)
#dashboard title
st.title("Real-time Dashboard")

current_time = datetime.now()
time_ranges = {
    '1h': current_time - timedelta(hours=1),
    '4h': current_time - timedelta(hours=4),
    '24h': current_time - timedelta(hours=24),
    '3d': current_time - timedelta(days=3),
    '7d': current_time - timedelta(days=7),
    '30d': current_time - timedelta(days=30),
    '90d': current_time - timedelta(days=90)
}
timeframe = {'1h','4h','24h','3d','7d','30d','90d'}
time_df = pd.DataFrame()  
time_range = st.selectbox("Select time frame:", timeframe, index = None,key='identifier1', placeholder="Choose a time frame")

placeholder = st.empty() #to make the effect refresh realtime
count = 0
filtered_data_close = None
filtered_data_open = None
if(time_range != None):
    label = time_range
    if label in time_ranges:
        selected_range = time_ranges[label]
        print(f"{label} time range starts from: {selected_range}")
    else:
        print(f"{label} is not a valid time range label.")
    closed.time = pd.to_datetime(closed.time)
    filtered_data_close = closed[
            (closed['time'] >= selected_range) & (closed['time'] <= current_time)
    ]
    opened.time = pd.to_datetime(opened.time)
    filtered_data_open = opened[
            (opened['time'] >= selected_range) & (opened['time'] <= current_time)
    ]
else :
    st.write("")

#place get to hold everything - single element container
def pre_process_open(df2):
    df2['stop_loss_pct'] = df2.apply(lambda x: (x['stop_loss'] / x['entry_price'] - 1)*x['leverage'] if x['direction'] == "BUY" 
    else (1 - x['stop_loss'] / x['entry_price'])*x['leverage']
    if not np.isnan(x['stop_loss']) else -1, axis=1)
    df2['take_profit_pct'] = df2.apply(lambda x: (x['take_profit']/x['entry_price']-1)*x['leverage'] if x['direction'] == "BUY" 
        else (1 - x['take_profit'] / x['entry_price'])*x['leverage'], axis=1)
    df2['take_profit_take'] = df2['margin_amount'] * df2['take_profit_pct']
    df2['stop_loss_give'] = df2['margin_amount'] * df2['stop_loss_pct']
    return df2

def pre_process_close(df1):
    df1=df1.dropna(axis=1)
    df1['volume'] = df1['leverage'] * df1['margin_amount']
    df1['close_price'] =df1['offer_amount']/df1['ask_amount']
    df1['close_pct'] = df1.apply(lambda x: (x['close_price'] / x['entry_price'] - 1)*x['leverage'] if x['direction'] == "BUY" else (1 - x['close_price'] / x['entry_price'])*x['leverage'], axis=1)
    df1['lose_amount'] =df1.apply(lambda x:(x['close_pct']*x['margin_amount']) if x['close_pct'] <0 else 0, axis = 1)
    df1['win_amount'] = df1.apply(lambda x: (x['close_pct']*x['margin_amount']) if x['close_pct'] >=0 else 0, axis = 1)
    return df1
#...real-time feed
def get_win_loss(df2):
    df = df2[['user_type','lose_amount','win_amount']]
    df = df.dropna()
    df = df.groupby('user_type').sum()
    return df
def get_amount(df2):
    df = df2[['direction','margin_amount','stop_loss_give','take_profit_take']]
    df = df.dropna()
    df = df.groupby('direction').sum()
    return df
def get_fee_funding(df2):
    df = df2[['user_type','fee','funding_payment']]
    df = df.dropna()
    df = df.groupby('user_type').sum()
    return df

#while True:
for seconds in range(200):
    #creating KPIs:

    #closed-win rate
    if((filtered_data_close is None) or len(filtered_data_close) == 0):
        st.write("No data available")
        break
    df1 = pre_process_close(filtered_data_close)
    df_fee = get_fee_funding(df1)
    df_close = get_win_loss(df1)
    win_amount_user = df_close.loc['USER']['win_amount']
    loss_amount_user = df_close.loc['USER']['lose_amount']
    win_amount_bot = df_close.loc['BOT']['win_amount']
    loss_amount_bot =  df_close.loc['BOT']['lose_amount']

    #opening positions
    df2 = pre_process_open(filtered_data_open)
    df_open = get_amount(df2)

    with placeholder.container():
        #create kpi metric
        kpi1,kpi2 = st.columns(2)
        print(type(kpi1))
        kpi1.metric("Closed-win rate - user", (win_amount_user/(win_amount_user+(-loss_amount_user))),10)
        kpi2.metric("Closed-win rate - bot", (win_amount_bot/(win_amount_bot+(-loss_amount_bot))),3)
        
        fig_close,fig_open, fig_funding = st.columns(3)
        with fig_close:
            st.markdown("### Closed-win rate by user_type")
            # fig1 = px.histogram(df, x=df.index, y="win_amount", color="win_amount", barmode="group", title="Closed-win rate by user_type")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_close.index,
                y=df_close['win_amount'],
                name='Win',
                marker=dict(color='green')
            ))
            fig.add_trace(go.Bar(
                x=df_close.index,
                y=df_close['lose_amount'],
                name='Loss',
                marker=dict(color='red')
            ))
            # Update layout
            fig.update_layout(
                barmode='group',  # To stack bars on top of each other
                xaxis=dict(title='Timeframe'),
                yaxis=dict(title='Amount ($)'),
                title='Loss and Earn Amounts Over Timeframe',
                legend=dict(title='Category')
            )
            st.write(fig)
        
        with fig_open:
            st.markdown("### Opening positions")
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=df_open.index,
                y=df_open['margin_amount'],
                name='margin_amount',
                marker=dict(color='blue')
            ))
            fig1.add_trace(go.Bar(
                x=df_open.index,
                y=df_open['stop_loss_give'],
                name='stop_loss_give',
                marker=dict(color='red')
            ))
            fig1.add_trace(go.Bar(
                x=df_open.index,
                y=df_open['take_profit_take'],
                name='take_profit_take',
                marker=dict(color='green')
            ))
            # Update layout
            fig1.update_layout(
                barmode='group', 
                xaxis=dict(title='Timeframe'),
                yaxis=dict(title='Amount ($)'),
                title='Opening tracking',
                legend=dict(title='Category')
            )
            st.write(fig1)
        with fig_funding:
            st.markdown("### Fee and Funding")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=df_fee.index,
                y=df_fee['fee'],
                name='fee',
                marker=dict(color='blue')
            ))
            fig2.add_trace(go.Bar(
                x=df_fee.index,
                y=df_fee['funding_payment'],
                name='funding_payment',
                marker=dict(color='red')
            ))
            # Update layout
            fig2.update_layout(
                barmode='group', 
                xaxis=dict(title='Timeframe'),
                yaxis=dict(title='Amount ($)'),
                title='Fee and Funding',
                legend=dict(title='Category')
            )
            st.write(fig2)
        time.sleep(0.5)
# st.markdown("### Detailed view")
# dataframe = {'Closed':filtered_data_close,'Opening':filtered_data_open}
# count +=1
# data = st.selectbox("Select dataframe to see:", ['Closed', 'Opening'], index = None, key = count, placeholder="Choose a data frame")
# if(data != None):
#     st.dataframe(dataframe[data])  
  

