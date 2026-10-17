import customtkinter as ctk
from datetime import datetime, date
from config import STOCKS, MONTHLY_INVEST, DEFAULT_GOAL, REFRESH_SECONDS, SECTOR_COLORS
from database import Database
from fetcher import DataFetcher, notify, upcoming_dividends

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# ── Palette ──────────────────────────────────────────────────────────
ACCENT = "#1DB97B"
BG_SIDE = "#1a1a1a"
BG_CARD = "#2b2b2b"
BG_ROW_A = "#2b2b2b"
BG_ROW_B = "#323232"
BG_HEAD = "#1f1f1f"
C_PRI = "#FFFFFF"
C_SEC = "#AAAAAA"
C_POS = "#4CAF50"
C_NEG = "#F44336"
C_WRN = "#EF9F27"


# ════════════════════════════════════════════════════════════════════
# REUSABLE WIDGETS
# ════════════════════════════════════════════════════════════════════
class MetricCard(ctk.CTkFrame):
    def __init__(self, parent, label, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, **kw)
        ctk.CTkLabel(self, text=label, font=("Arial", 11),
                     text_color=C_SEC).pack(pady=(12, 2), padx=14)
        self._val = ctk.CTkLabel(self, text="—", font=("Arial", 20, "bold"),
                                 text_color=C_PRI)
        self._val.pack(pady=(0, 12), padx=14)

    def update(self, text, color=C_PRI):
        self._val.configure(text=text, text_color=color)


def _table_header(parent, columns):
    hdr = ctk.CTkFrame(parent, fg_color=BG_HEAD, corner_radius=0, height=36)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    for label, width, anchor in columns:
        ctk.CTkLabel(hdr, text=label, font=("Arial", 11, "bold"),
                     text_color=C_SEC, width=width, anchor=anchor
                     ).pack(side="left", padx=(10, 0))
    return hdr


# ════════════════════════════════════════════════════════════════════
# DASHBOARD VIEW
# ════════════════════════════════════════════════════════════════════
class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, db, fetcher, app_ref):
        super().__init__(parent, fg_color="transparent")
        self.db, self.fetcher, self.app_ref = db, fetcher, app_ref
        self._rows_built = False
        self._row_labels = {}
        self._build()

    def _build(self):
        # Title
        ctk.CTkLabel(self, text="Portfolio Overview",
                     font=("Arial", 18, "bold"), text_color=C_PRI
                     ).pack(anchor="w", pady=(0, 14))

        # Metric cards
        cf = ctk.CTkFrame(self, fg_color="transparent")
        cf.pack(fill="x", pady=(0, 12))
        self.cards = {}
        card_defs = [
            ('invested', 'Total Invested'),
            ('value', 'Current Value'),
            ('pnl', 'P&L'),
            ('yield', 'Avg Yield on Cost'),
            ('monthly', 'Monthly Income'),
        ]
        for i, (key, lbl) in enumerate(card_defs):
            c = MetricCard(cf, lbl)
            c.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="ew")
            cf.columnconfigure(i, weight=1)
            self.cards[key] = c

        # Goal progress card
        gf = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        gf.pack(fill="x", pady=(0, 12))

        top = ctk.CTkFrame(gf, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(top, text="Monthly Income Goal",
                     font=("Arial", 13, "bold"), text_color=C_PRI).pack(side="left")
        self.goal_lbl = ctk.CTkLabel(top, text="€0.00 / €500.00",
                                     font=("Arial", 12), text_color=C_SEC)
        self.goal_lbl.pack(side="right")

        self.progress = ctk.CTkProgressBar(gf, progress_color=ACCENT, height=8)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=16, pady=(0, 4))

        self.pct_lbl = ctk.CTkLabel(gf, text="0.0% of goal reached",
                                    font=("Arial", 11), text_color=C_SEC)
        self.pct_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        # Stock table
        tf = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        tf.pack(fill="both", expand=True)

        _table_header(tf, [
            ("Stock", 190, "w"),
            ("Shares", 80, "e"),
            ("Live Price €", 105, "e"),
            ("Value €", 100, "e"),
            ("Yield on Cost", 110, "e"),
            ("Monthly €", 100, "e"),
        ])

        self.table_body = ctk.CTkScrollableFrame(tf, fg_color="transparent")
        self.table_body.pack(fill="both", expand=True)

        # Last updated
        self.upd_lbl = ctk.CTkLabel(self, text="Fetching live prices...",
                                    font=("Arial", 10), text_color=C_SEC)
        self.upd_lbl.pack(anchor="e", pady=(6, 0))

    def _build_rows(self):
        for w in self.table_body.winfo_children():
            w.destroy()
        self._row_labels = {}

        for i, (ticker, cfg) in enumerate(STOCKS.items()):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            color = SECTOR_COLORS.get(cfg['sector'], '#888888')

            row = ctk.CTkFrame(self.table_body, fg_color=bg, corner_radius=0, height=42)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Name + ticker column
            nf = ctk.CTkFrame(row, fg_color="transparent", width=190)
            nf.pack(side="left", padx=(10, 0))
            nf.pack_propagate(False)
            ctk.CTkLabel(nf, text=cfg['name'][:20], font=("Arial", 12, "bold"),
                         text_color=C_PRI, anchor="w").pack(anchor="w", pady=(6, 0))
            ctk.CTkLabel(nf, text=ticker, font=("Arial", 10),
                         text_color=color, anchor="w").pack(anchor="w")

            lbls = {}
            for key, width in [('shares', 80), ('price', 105),
                               ('value', 100), ('yield', 110), ('monthly', 100)]:
                l = ctk.CTkLabel(row, text="—", font=("Arial", 12),
                                 text_color=C_SEC, width=width, anchor="e")
                l.pack(side="left", padx=(4, 0))
                lbls[key] = l

            self._row_labels[ticker] = lbls

        self._rows_built = True

    def refresh(self):
        if not self._rows_built:
            self._build_rows()

        holdings = self.db.get_holdings()
        market_data = self.fetcher.market_data()
        goal = float(self.db.get('goal', DEFAULT_GOAL))

        total_invested = 0.0
        total_value = 0.0
        total_annual = 0.0

        for ticker in STOCKS:
            h = holdings.get(ticker)
            m = market_data.get(ticker, {})
            lbls = self._row_labels.get(ticker, {})

            if not h or not h.get('shares'):
                for l in lbls.values():
                    l.configure(text="—", text_color=C_SEC)
                continue

            shares = h['shares']
            avg_cost = h['avg_cost']
            price = m.get('price', 0)
            div = m.get('div_per_share', 0)

            invested = shares * avg_cost
            value = shares * price if price else invested
            annual = shares * div
            monthly = annual / 12
            yoc = (div / avg_cost * 100) if avg_cost else 0

            total_invested += invested
            total_value += value
            total_annual += annual

            yoc_color = C_POS if yoc >= 4 else (C_WRN if yoc >= 2 else C_SEC)

            lbls['shares'].configure(text=f"{shares:.3f}", text_color=C_PRI)
            lbls['price'].configure(text=f"€{price:.2f}" if price else "—",
                                    text_color=C_PRI)
            lbls['value'].configure(text=f"€{value:.2f}", text_color=C_PRI)
            lbls['yield'].configure(text=f"{yoc:.2f}%", text_color=yoc_color)
            lbls['monthly'].configure(text=f"€{monthly:.2f}",
                                      text_color=ACCENT if monthly > 0 else C_SEC)

        pnl = total_value - total_invested
        avg_yld = (total_annual / total_invested * 100) if total_invested else 0
        monthly = total_annual / 12

        self.cards['invested'].update(f"€{total_invested:,.2f}")
        self.cards['value'].update(f"€{total_value:,.2f}")
        self.cards['pnl'].update(
            f"{'+' if pnl >= 0 else ''}€{pnl:,.2f}",
            C_POS if pnl >= 0 else C_NEG
        )
        self.cards['yield'].update(f"{avg_yld:.2f}%")
        self.cards['monthly'].update(f"€{monthly:.2f}", ACCENT)

        pct = min(monthly / goal, 1.0) if goal else 0
        self.progress.set(pct)
        self.goal_lbl.configure(text=f"€{monthly:.2f} / €{goal:.0f} per month")
        self.pct_lbl.configure(
            text=f"{pct * 100:.1f}% of goal reached" + (" ✓" if pct >= 1 else "")
        )

        if market_data:
            dates = [d.get('updated_at') for d in market_data.values() if d.get('updated_at')]
            if dates:
                try:
                    dt = datetime.fromisoformat(max(dates))
                    self.upd_lbl.configure(text=f"Last updated: {dt.strftime('%H:%M:%S')}")
                except:
                    pass


# ════════════════════════════════════════════════════════════════════
# PURCHASES VIEW
# ════════════════════════════════════════════════════════════════════
class PurchasesView(ctk.CTkFrame):
    def __init__(self, parent, db, fetcher, app_ref):
        super().__init__(parent, fg_color="transparent")
        self.db, self.fetcher, self.app_ref = db, fetcher, app_ref
        self._build()

    def _build(self):
        # ── Left panel: form ─────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, width=295)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Add Purchase",
                     font=("Arial", 15, "bold"), text_color=C_PRI
                     ).pack(pady=(18, 10), padx=18, anchor="w")

        def field(label, placeholder, ref_name):
            ctk.CTkLabel(left, text=label, font=("Arial", 11),
                         text_color=C_SEC).pack(anchor="w", padx=18)
            e = ctk.CTkEntry(left, placeholder_text=placeholder,
                             font=("Arial", 12), width=255, height=34)
            e.pack(padx=18, pady=(2, 10))
            setattr(self, ref_name, e)

        # Ticker dropdown
        ctk.CTkLabel(left, text="Stock", font=("Arial", 11),
                     text_color=C_SEC).pack(anchor="w", padx=18)
        self.ticker_cb = ctk.CTkComboBox(
            left, values=list(STOCKS.keys()), font=("Arial", 12),
            width=255, height=34,
            command=self._autofill_price
        )
        self.ticker_cb.pack(padx=18, pady=(2, 10))

        field("Shares", "e.g.  1.500", "shares_e")
        field("Price Paid (€)", "e.g.  61.50", "price_e")
        field("Date (YYYY-MM-DD)", date.today().isoformat(), "date_e")
        self.date_e.insert(0, date.today().isoformat())

        self.msg = ctk.CTkLabel(left, text="", font=("Arial", 11), text_color=C_POS)
        self.msg.pack(padx=18, anchor="w")

        ctk.CTkButton(
            left, text="Add Purchase", font=("Arial", 13, "bold"),
            fg_color=ACCENT, hover_color="#17845a",
            height=38, width=255, command=self._add
        ).pack(padx=18, pady=(8, 4))

        # Divider
        ctk.CTkFrame(left, fg_color="#3a3a3a", height=1).pack(fill="x", padx=18, pady=14)

        # AutoInvest section (Default)
        ctk.CTkLabel(left, text="AutoInvest",
                     font=("Arial", 14, "bold"), text_color=C_PRI
                     ).pack(anchor="w", padx=18)
        ctk.CTkLabel(left,
                     text=f"Log €{MONTHLY_INVEST} split across all\n12 stocks at today's prices",
                     font=("Arial", 11), text_color=C_SEC, justify="left"
                     ).pack(anchor="w", padx=18, pady=(2, 10))
        ctk.CTkButton(
            left, text=f"⚡  Log AutoInvest  (€{MONTHLY_INVEST})",
            font=("Arial", 13, "bold"),
            fg_color="#4A3F9F", hover_color="#332d7a",
            height=38, width=255, command=self._autoinvest
        ).pack(padx=18, pady=(0, 10))

        # --- NEW: Custom AutoInvest Section ---
        ctk.CTkFrame(left, fg_color="#3a3a3a", height=1).pack(fill="x", padx=18, pady=10)

        ctk.CTkLabel(left, text="Custom Allocation",
                     font=("Arial", 12, "bold"), text_color=C_PRI
                     ).pack(anchor="w", padx=18)

        custom_frame = ctk.CTkFrame(left, fg_color="transparent")
        custom_frame.pack(fill="x", padx=18, pady=(8, 18))

        self.custom_amount_e = ctk.CTkEntry(custom_frame, placeholder_text="e.g. 20",
                                            font=("Arial", 12), width=125, height=34)
        self.custom_amount_e.pack(side="left")

        ctk.CTkButton(
            custom_frame, text="⚡ Log Custom",
            font=("Arial", 12, "bold"),
            fg_color="#4A3F9F", hover_color="#332d7a",
            height=34, width=120, command=self._trigger_custom_autoinvest
        ).pack(side="right")

        # ── Right panel: history ─────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        right.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(right, text="Purchase History",
                     font=("Arial", 15, "bold"), text_color=C_PRI
                     ).pack(anchor="w", padx=18, pady=(18, 8))

        _table_header(right, [
            ("Date", 110, "w"),
            ("Ticker", 70, "w"),
            ("Shares", 90, "e"),
            ("Price Paid", 110, "e"),
            ("Total Cost", 110, "e"),
            ("", 50, "w"),
        ])

        self.hist = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.hist.pack(fill="both", expand=True)

    def _autofill_price(self, ticker):
        price = self.fetcher.market_data().get(ticker, {}).get('price', 0)
        if price:
            self.price_e.delete(0, "end")
            self.price_e.insert(0, f"{price:.2f}")

    def _add(self):
        ticker = self.ticker_cb.get().strip().upper()
        try:
            shares = float(self.shares_e.get().replace(',', '.'))
            price = float(self.price_e.get().replace(',', '.'))
            dt = self.date_e.get().strip() or date.today().isoformat()
            assert shares > 0 and price > 0
        except:
            self.msg.configure(text="⚠  Check your values", text_color=C_NEG)
            return

        self.db.add_purchase(ticker, shares, price, dt)
        self.shares_e.delete(0, "end")
        self.msg.configure(text=f"✓  Added {shares:.3f} × {ticker}", text_color=C_POS)
        self.refresh()
        self.app_ref.refresh_views()

    def _trigger_custom_autoinvest(self):
        try:
            amount = float(self.custom_amount_e.get().replace(',', '.'))
            assert amount > 0
            self._autoinvest(custom_amount=amount)
            self.msg.configure(text="", text_color=C_POS)
        except:
            self.msg.configure(text="⚠  Enter a valid custom amount", text_color=C_NEG)

    def _autoinvest(self, custom_amount=None):
        md = self.fetcher.market_data()
        if not md:
            self.msg.configure(text="⚠  Prices not loaded yet", text_color=C_NEG)
            return

        invest_amount = custom_amount if custom_amount is not None else MONTHLY_INVEST

        top = ctk.CTkToplevel(self)
        top.title("AutoInvest — Preview")
        top.geometry("440x540")
        top.resizable(False, False)
        top.grab_set()
        top.lift()
        top.focus_force()

        ctk.CTkLabel(top, text="AutoInvest Preview",
                     font=("Arial", 16, "bold"), text_color=C_PRI).pack(pady=(18, 2))
        ctk.CTkLabel(top, text=f"€{invest_amount} split across 12 stocks at live prices",
                     font=("Arial", 11), text_color=C_SEC).pack(pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(top, height=320)
        scroll.pack(fill="x", padx=16)

        purchases = []
        today_str = date.today().isoformat()

        for ticker, cfg in STOCKS.items():
            alloc = invest_amount * cfg['weight']
            price = md.get(ticker, {}).get('price', 0)
            if not price:
                continue
            shares = alloc / price
            purchases.append((ticker, shares, price, today_str))

            row = ctk.CTkFrame(scroll, fg_color=BG_ROW_B, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=ticker, font=("Arial", 12, "bold"),
                         text_color=C_PRI, width=55, anchor="w"
                         ).pack(side="left", padx=(10, 0), pady=8)
            ctk.CTkLabel(
                row,
                text=f"€{alloc:.2f}  →  {shares:.4f} sh  @  €{price:.2f}",
                font=("Arial", 11), text_color=C_SEC
            ).pack(side="left", padx=8)

        def _confirm():
            for p in purchases:
                self.db.add_purchase(*p)
            top.destroy()
            self.refresh()
            self.app_ref.refresh_views()
            if custom_amount is not None:
                self.custom_amount_e.delete(0, "end")
            notify("AutoInvest Logged ✓",
                   f"€{invest_amount} logged across {len(purchases)} stocks")

        ctk.CTkButton(top, text="✓  Confirm & Log All",
                      font=("Arial", 13, "bold"),
                      fg_color=ACCENT, hover_color="#17845a",
                      height=40, command=_confirm).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkButton(top, text="Cancel", fg_color="#444",
                      hover_color="#555", height=34,
                      command=top.destroy).pack(fill="x", padx=16)

    def refresh(self):
        for w in self.hist.winfo_children():
            w.destroy()

        purchases = self.db.get_purchases()
        if not purchases:
            ctk.CTkLabel(self.hist, text="No purchases yet — add one or use AutoInvest",
                         font=("Arial", 12), text_color=C_SEC).pack(pady=24)
            return

        for i, p in enumerate(purchases):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            row = ctk.CTkFrame(self.hist, fg_color=bg, corner_radius=0, height=36)
            row.pack(fill="x")
            row.pack_propagate(False)

            total = p['shares'] * p['price_paid']
            for text, width, anchor in [
                (p['date_bought'], 110, "w"),
                (p['ticker'], 70, "w"),
                (f"{p['shares']:.4f}", 90, "e"),
                (f"€{p['price_paid']:.2f}", 110, "e"),
                (f"€{total:.2f}", 110, "e"),
            ]:
                ctk.CTkLabel(row, text=text, font=("Arial", 11),
                             text_color=C_PRI, width=width, anchor=anchor
                             ).pack(side="left", padx=(10, 0))

            def _del(pid=p['id']):
                self.db.delete_purchase(pid)
                self.refresh()
                self.app_ref.refresh_views()

            ctk.CTkButton(row, text="✕", width=32, height=24,
                          font=("Arial", 10), fg_color="#555",
                          hover_color=C_NEG, text_color=C_PRI,
                          command=_del).pack(side="left", padx=8)


# ════════════════════════════════════════════════════════════════════
# PROJECTIONS VIEW (UPDATED WITH DRIP SWITCH ENGINE)
# ════════════════════════════════════════════════════════════════════
class ProjectionsView(ctk.CTkFrame):
    def __init__(self, parent, db, fetcher, app_ref):
        super().__init__(parent, fg_color="transparent")
        self.db, self.fetcher, self.app_ref = db, fetcher, app_ref

        # New global switch state container for Projections
        self.reinvest_dividends = ctk.BooleanVar(value=True)
        self._build()

    def _build(self):
        # Top panel wrapper to place switch alongside title smoothly
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(anchor="w", fill="x", pady=(0, 2))

        ctk.CTkLabel(top_bar, text="Income Projections",
                     font=("Arial", 18, "bold"), text_color=C_PRI).pack(side="left")

        # Interactive CustomTkinter Switch
        self.reinvest_switch = ctk.CTkSwitch(
            top_bar,
            text="Reinvest Dividends (DRIP)",
            variable=self.reinvest_dividends,
            onvalue=True,
            offvalue=False,
            command=self.refresh,
            progress_color=ACCENT
        )
        self.reinvest_switch.pack(side="right", padx=5)

        self.sub_lbl = ctk.CTkLabel(self, text="", font=("Arial", 11), text_color=C_SEC)
        self.sub_lbl.pack(anchor="w", pady=(2, 14))

        tf = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        tf.pack(fill="both", expand=True)

        _table_header(tf, [
            ("Horizon", 120, "w"),
            ("Months", 75, "e"),
            ("Extra Invested", 140, "e"),
            ("Portfolio Value", 150, "e"),
            ("Annual Income", 140, "e"),
            ("Monthly Income", 140, "e"),
            ("Portfolio Yield", 140, "e"),
        ])

        self.body = ctk.CTkScrollableFrame(tf, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

        ctk.CTkLabel(self,
                     text="Green = monthly income has reached your goal",
                     font=("Arial", 10, "italic"), text_color=C_SEC
                     ).pack(anchor="w", pady=(8, 0))

    def refresh(self):
        for w in self.body.winfo_children():
            w.destroy()

        holdings = self.db.get_holdings()
        market_data = self.fetcher.market_data()
        goal = float(self.db.get('goal', DEFAULT_GOAL))

        if not market_data:
            ctk.CTkLabel(self.body, text="Waiting for live prices...",
                         font=("Arial", 12), text_color=C_SEC).pack(pady=24)
            return

        # Dynamic subtitles highlighting if DRIP is compounding calculations live
        if self.reinvest_dividends.get():
            self.sub_lbl.configure(
                text=f"Assumes €{MONTHLY_INVEST}/month AutoInvest continues + Dividends Reinvested (DRIP) — prices held constant")
        else:
            self.sub_lbl.configure(
                text=f"Assumes €{MONTHLY_INVEST}/month AutoInvest continues (Dividends Paid as Cash) — prices held constant")

        cur_invested = sum(
            (holdings.get(tk, {}).get('total_cost') or 0) for tk in STOCKS
        )

        horizons = [
            ("Current", 0),
            ("6 Months", 6),
            ("1 Year", 12),
            ("2 Years", 24),
            ("3 Years", 36),
            ("5 Years", 60),
            ("10 Years", 120),
        ]

        for i, (label, months) in enumerate(horizons):
            sim = {tk: (holdings.get(tk, {}).get('shares') or 0) for tk in STOCKS}

            # Step month-by-month to accurately track compounding logic
            for _ in range(months):
                # 1. If DRIP toggle is activated, distribute monthly cash rewards into new fractional shares first
                if self.reinvest_dividends.get():
                    for tk in STOCKS:
                        p = market_data.get(tk, {}).get('price', 0)
                        div_per_share = market_data.get(tk, {}).get('div_per_share', 0)
                        if p and div_per_share and sim[tk] > 0:
                            monthly_div_payout = sim[tk] * (div_per_share / 12)
                            sim[tk] += monthly_div_payout / p

                # 2. Drop standard monthly €120 allocation weights across the Pie components
                for tk, cfg in STOCKS.items():
                    p = market_data.get(tk, {}).get('price', 0)
                    if p:
                        sim[tk] += (MONTHLY_INVEST * cfg['weight']) / p

            fut_value = sum(sim[tk] * (market_data.get(tk, {}).get('price', 0) or 0)
                            for tk in STOCKS)
            fut_annual = sum(sim[tk] * (market_data.get(tk, {}).get('div_per_share', 0) or 0)
                             for tk in STOCKS)
            fut_mo = fut_annual / 12
            extra = MONTHLY_INVEST * months
            total_inv = cur_invested + extra
            yop = (fut_annual / total_inv * 100) if total_inv else 0

            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            mo_color = C_POS if fut_mo >= goal else C_PRI
            bold = "bold" if label == "Current" else "normal"

            row = ctk.CTkFrame(self.body, fg_color=bg, corner_radius=0, height=44)
            row.pack(fill="x")
            row.pack_propagate(False)

            for text, width, color, anchor in [
                (label, 120, C_PRI, "w"),
                (str(months), 75, C_SEC, "e"),
                (f"€{extra:,.0f}", 140, C_SEC, "e"),
                (f"€{fut_value:,.2f}", 150, C_PRI, "e"),
                (f"€{fut_annual:,.2f}", 140, C_PRI, "e"),
                (f"€{fut_mo:,.2f}", 140, mo_color, "e"),
                (f"{yop:.2f}%", 140, C_SEC, "e"),
            ]:
                ctk.CTkLabel(row, text=text, font=("Arial", 12, bold),
                             text_color=color, width=width, anchor=anchor
                             ).pack(side="left", padx=(10, 0))


# ════════════════════════════════════════════════════════════════════
# SETTINGS VIEW
# ════════════════════════════════════════════════════════════════════
class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, db, fetcher, app_ref):
        super().__init__(parent, fg_color="transparent")
        self.db, self.fetcher, self.app_ref = db, fetcher, app_ref
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Settings",
                     font=("Arial", 18, "bold"), text_color=C_PRI).pack(anchor="w", pady=(0, 18))

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        card.pack(fill="x")

        ctk.CTkLabel(card, text="Monthly Income Goal (€)",
                     font=("Arial", 13, "bold"), text_color=C_PRI
                     ).pack(anchor="w", padx=18, pady=(16, 2))
        ctk.CTkLabel(card, text="The target you're working toward — shown as a progress bar on the dashboard",
                     font=("Arial", 11), text_color=C_SEC).pack(anchor="w", padx=18, pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))

        self.goal_e = ctk.CTkEntry(row, placeholder_text="500",
                                   font=("Arial", 13), width=160, height=36)
        self.goal_e.pack(side="left")
        self.goal_e.insert(0, self.db.get('goal', str(DEFAULT_GOAL)))

        self.goal_msg = ctk.CTkLabel(row, text="", font=("Arial", 11), text_color=C_POS)
        self.goal_msg.pack(side="left", padx=12)

        ctk.CTkButton(row, text="Save", font=("Arial", 12, "bold"),
                      fg_color=ACCENT, hover_color="#17845a",
                      width=90, height=36, command=self._save_goal
                      ).pack(side="left")

        ctk.CTkFrame(card, fg_color="#3a3a3a", height=1).pack(fill="x", padx=18, pady=4)
        rate_row = ctk.CTkFrame(card, fg_color="transparent")
        rate_row.pack(fill="x", padx=18, pady=12)
        ctk.CTkLabel(rate_row, text="EUR / USD Rate",
                     font=("Arial", 13, "bold"), text_color=C_PRI).pack(side="left")
        self.rate_lbl = ctk.CTkLabel(rate_row,
                                     text=f"{self.fetcher.eur_usd:.4f}  (auto-updated)",
                                     font=("Arial", 12), text_color=C_SEC)
        self.rate_lbl.pack(side="left", padx=12)

    def _save_goal(self):
        try:
            g = float(self.goal_e.get())
            assert g > 0
            self.db.set('goal', g)
            self.goal_msg.configure(text="✓ Saved", text_color=C_POS)
            self.app_ref.refresh_views()
        except:
            self.goal_msg.configure(text="⚠ Invalid", text_color=C_NEG)

    def refresh(self):
        self.rate_lbl.configure(text=f"{self.fetcher.eur_usd:.4f}  (auto-updated)")


# ════════════════════════════════════════════════════════════════════
# MAIN APP WINDOW
# ════════════════════════════════════════════════════════════════════
class DividendTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dividend Tracker")
        self.geometry("1200x740")
        self.minsize(960, 620)

        self.db = Database()
        self.fetcher = DataFetcher(self.db)

        self._active = None
        self._nav = {}

        self._build_layout()
        self._build_sidebar()
        self._build_views()
        self._switch("dashboard")
        self._start_refresh()

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=215, corner_radius=0, fg_color=BG_SIDE)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.content = ctk.CTkFrame(self, fg_color="#242424", corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_sidebar(self):
        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", pady=(22, 20), padx=16)
        ctk.CTkLabel(logo, text="💹", font=("Arial", 32)).pack()
        ctk.CTkLabel(logo, text="Dividend Tracker",
                     font=("Arial", 14, "bold"), text_color=C_PRI,
                     justify="center").pack()

        ctk.CTkFrame(self.sidebar, fg_color="#333333", height=1).pack(fill="x", padx=14, pady=(0, 12))

        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("purchases", "💰  Purchases"),
            ("projections", "📈  Projections"),
            ("settings", "⚙️   Settings"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=("Arial", 13), height=40, corner_radius=8,
                fg_color="transparent", hover_color="#2a2a2a",
                text_color=C_SEC,
                command=lambda k=key: self._switch(k)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav[key] = btn

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)

        sb = ctk.CTkFrame(self.sidebar, fg_color="#252525", corner_radius=8)
        sb.pack(fill="x", padx=10, pady=(0, 8))
        self.dot_lbl = ctk.CTkLabel(sb, text="● Offline",
                                    font=("Arial", 11), text_color="#777")
        self.dot_lbl.pack(anchor="w", padx=12, pady=(8, 2))
        self.rate_lbl = ctk.CTkLabel(sb, text=f"EUR/USD  {self.fetcher.eur_usd:.4f}",
                                     font=("Arial", 10), text_color=C_SEC)
        self.rate_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        ctk.CTkButton(
            self.sidebar, text="🔄  Refresh Prices",
            font=("Arial", 12), height=34, corner_radius=8,
            fg_color="#2a2a2a", hover_color="#333",
            command=self._manual_refresh
        ).pack(fill="x", padx=10, pady=(0, 16))

    def _build_views(self):
        self._views = {}
        for key, Cls in [
            ("dashboard", DashboardView),
            ("purchases", PurchasesView),
            ("projections", ProjectionsView),
            ("settings", SettingsView),
        ]:
            v = Cls(self.content, self.db, self.fetcher, self)
            v.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
            v.grid_remove()
            self._views[key] = v

    def _switch(self, key):
        for k, v in self._views.items():
            v.grid_remove()
            self._nav[k].configure(fg_color="transparent", text_color=C_SEC)
        self._views[key].grid()
        self._nav[key].configure(fg_color="#2d2d2d", text_color=C_PRI)
        self._active = key
        self._views[key].refresh()

    def refresh_views(self):
        if self._active:
            self._views[self._active].refresh()

    def _on_fetch_done(self):
        self.after(0, self._post_fetch)

    def _post_fetch(self):
        self.dot_lbl.configure(text="● Live", text_color=C_POS)
        self.rate_lbl.configure(text=f"EUR/USD  {self.fetcher.eur_usd:.4f}")
        self.refresh_views()

        for a in upcoming_dividends(self.fetcher.market_data()):
            notify(f"{a['ticker']}  Ex-Dividend Soon",
                   f"Ex-div date: {a['ex_date']} — make sure you hold shares before this date!")

    def _start_refresh(self):
        self.dot_lbl.configure(text="● Loading...", text_color=C_WRN)
        self.fetcher.fetch_all(list(STOCKS.keys()), on_complete=self._on_fetch_done)
        self.after(REFRESH_SECONDS * 1000, self._auto_refresh)

    def _auto_refresh(self):
        self.dot_lbl.configure(text="● Refreshing...", text_color=C_WRN)
        self.fetcher.fetch_all(list(STOCKS.keys()), on_complete=self._on_fetch_done)
        self.after(REFRESH_SECONDS * 1000, self._auto_refresh)

    def _manual_refresh(self):
        self.dot_lbl.configure(text="● Refreshing...", text_color=C_WRN)
        self.fetcher.fetch_all(list(STOCKS.keys()), on_complete=self._on_fetch_done)

    def on_closing(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = DividendTrackerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()