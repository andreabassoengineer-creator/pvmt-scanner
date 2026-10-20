import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# Configurazione Pagina per Mobile
st.set_page_config(
    page_title="PVMT 3:1 Scanner", page_icon="📈", layout="wide"
)

st.title("📈 Scanner PVMT 3:1 Global di Andrea Basso")
st.caption(
    "Protocollo Meccanico di Validazione del Trade (Allocazione 1.000€) utile"
    " per trovare azioni che rispettino lo stop loss al 3% e il take profit al 9%"
    " valutando la volatilità del titolo."
)

BUDGET_PER_POSIZIONE_EUR = 1000.0
MOLTIPLICATORE_ATR_SL = 1.5

# Dizionario Ticker -> (Bandiera/Sigla Paese, Nome Azienda)
INFO_TICKERS = {
    # Italia 🇮🇹
    "RACE.MI": ("🇮🇹 IT", "Ferrari N.V."),
    "STM.MI": ("🇮🇹 IT", "STMicroelectronics"),
    "UCG.MI": ("🇮🇹 IT", "UniCredit S.p.A."),
    "ISP.MI": ("🇮🇹 IT", "Intesa Sanpaolo"),
    "ENI.MI": ("🇮🇹 IT", "Eni S.p.A."),
    "ENEL.MI": ("🇮🇹 IT", "Enel S.p.A."),
    "STLAM.MI": ("🇮🇹 IT", "Stellantis N.V."),
    "G.MI": ("🇮🇹 IT", "Assicurazioni Generali"),
    "MONC.MI": ("🇮🇹 IT", "Moncler S.p.A."),
    "BMPS.MI": ("🇮🇹 IT", "Banca Monte dei Paschi"),
    "A2A.MI": ("🇮🇹 IT", "A2A S.p.A."),
    # Francia 🇫🇷
    "EL.PA": ("🇫🇷 FR", "EssilorLuxottica"),
    "MC.PA": ("🇫🇷 FR", "LVMH Moët Hennessy"),
    "SU.PA": ("🇫🇷 FR", "Schneider Electric"),
    "TTE.PA": ("🇫🇷 FR", "TotalEnergies SE"),
    # Olanda / Germania / Spagna 🇳🇱 🇩🇪 🇪🇸
    "ASML.AS": ("🇳🇱 NL", "ASML Holding N.V."),
    "SAP.DE": ("🇩🇪 DE", "SAP SE"),
    "IBE.MC": ("🇪🇸 ES", "Iberdrola S.A."),
    "SAN.MC": ("🇪🇸 ES", "Banco Santander"),
    # USA 🇺🇸
    "AAPL": ("🇺🇸 US", "Apple Inc."),
    "MSFT": ("🇺🇸 US", "Microsoft Corp."),
    "NVDA": ("🇺🇸 US", "NVIDIA Corp."),
    "AMZN": ("🇺🇸 US", "Amazon.com Inc."),
    "GOOGL": ("🇺🇸 US", "Alphabet Inc."),
    "META": ("🇺🇸 US", "Meta Platforms Inc."),
    "TSLA": ("🇺🇸 US", "Tesla Inc."),
}

LISTA_TICKERS = list(INFO_TICKERS.keys())

if st.button("🚀 Esegui Scanner Ora", use_container_width=True):
  with st.spinner("Analisi dei mercati in corso..."):
    fx_df = yf.download("EURUSD=X", period="5d", progress=False)
    tasso_eur_usd = float(fx_df["Close"].iloc[-1].item())

    data = yf.download(
        LISTA_TICKERS,
        period="1y",
        interval="1d",
        progress=False,
        group_by="ticker",
    )

    risultati_validati = []
    risultati_esclusi = []
    totale_analizzati = len(LISTA_TICKERS)

    for ticker in LISTA_TICKERS:
      paese, azienda = INFO_TICKERS.get(ticker, ("🌐 --", ticker))

      try:
        df = data[ticker].dropna() if len(LISTA_TICKERS) > 1 else data.dropna()

        if df.empty or len(df) < 200:
          risultati_esclusi.append({
              "Paese": paese,
              "Azienda": azienda,
              "Ticker": ticker,
              "Motivo Esclusione": "Dati storici insufficienti (< 200 giorni)",
          })
          continue

        is_usa = "." not in ticker
        budget_allocato = (
            BUDGET_PER_POSIZIONE_EUR * tasso_eur_usd
            if is_usa
            else BUDGET_PER_POSIZIONE_EUR
        )
        simbolo_valuta = "$" if is_usa else "€"

        sma_200_val = float(
            df["Close"].rolling(window=200).mean().iloc[-1].item()
        )
        prezzo_corrente = float(df["Close"].iloc[-1].item())

        # Filtro SMA 200
        if prezzo_corrente <= sma_200_val:
          risultati_esclusi.append({
              "Paese": paese,
              "Azienda": azienda,
              "Ticker": ticker,
              "Motivo Esclusione": (
                  f"Prezzo ({round(prezzo_corrente, 2)} {simbolo_valuta}) "
                  f"sotto la SMA 200 ({round(sma_200_val, 2)})"
              ),
          })
          continue

        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(
            axis=1
        )
        atr_val = float(true_range.rolling(window=14).mean().iloc[-1].item())

        distanza_sl = MOLTIPLICATORE_ATR_SL * atr_val
        sl = prezzo_corrente - distanza_sl
        tp = prezzo_corrente + (3 * distanza_sl)

        perc_sl = (distanza_sl / prezzo_corrente) * 100
        perc_tp = (3 * distanza_sl / prezzo_corrente) * 100

        num_azioni = int(budget_allocato / prezzo_corrente)
        controvalore_nominale = num_azioni * prezzo_corrente
        controvalore_eur = (
            controvalore_nominale / tasso_eur_usd
            if is_usa
            else controvalore_nominale
        )

        if num_azioni > 0:
          risultati_validati.append({
              "Paese": paese,
              "Azienda": azienda,
              "Ticker": ticker,
              "Prezzo": f"{round(prezzo_corrente, 2)} {simbolo_valuta}",
              "SMA 200": round(sma_200_val, 2),
              "Stop Loss": f"{round(sl, 2)} (-{round(perc_sl, 2)}%)",
              "Take Profit": f"{round(tp, 2)} (+{round(perc_tp, 2)}%)",
              "Q.tà": num_azioni,
              "Allocato (EUR)": f"{round(controvalore_eur, 2)} €",
          })
        else:
          risultati_esclusi.append({
              "Paese": paese,
              "Azienda": azienda,
              "Ticker": ticker,
              "Motivo Esclusione": (
                  f"Prezzo troppo alto ({round(prezzo_corrente, 2)} "
                  f"{simbolo_valuta}) per l'allocazione di 1.000 €"
              ),
          })
      except Exception as e:
        risultati_esclusi.append({
            "Paese": paese,
            "Azienda": azienda,
            "Ticker": ticker,
            "Motivo Esclusione": "Errore nel recupero dati",
        })

    # --- TABELLA TITOLI IDONEI ---
    if risultati_validati:
      st.success(
          f"Tasso cambio applicato: 1 EUR = {tasso_eur_usd:.4f} USD. Trovati"
          f" {len(risultati_validati)} titoli idonei di {totale_analizzati}"
          " analizzati!"
      )
      df_out = pd.DataFrame(risultati_validati)
      st.dataframe(df_out, use_container_width=True, hide_index=True)
    else:
      st.warning(f"Trovati 0 titoli idonei di {totale_analizzati} analizzati.")

    # --- TABELLA TITOLI ESCLUSI ---
    if risultati_esclusi:
      st.markdown("---")
      st.subheader(f"❌ Titoli Esclusi dal Protocollo ({len(risultati_esclusi)})")
      df_esclusi = pd.DataFrame(risultati_esclusi)
      st.dataframe(df_esclusi, use_container_width=True, hide_index=True)
