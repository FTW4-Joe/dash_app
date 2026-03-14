# In[1]:
#DASH App

# In[2]:
#Import modules
import requests
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px

# In[3]:
#Loading full datasets from hugging face
dataset = load_dataset("bettergovph/dpwh-transparency-data")
df = dataset['train'].to_pandas()

# In[4]:
# Ensure numeric
df['infraYear'] = pd.to_numeric(df['infraYear'], errors='coerce')
df['budget'] = pd.to_numeric(df['budget'], errors='coerce')

# Convert completionDate to year (if exists)
if 'completionDate' in df.columns:
    df['completionDate'] = pd.to_datetime(df['completionDate'], errors='coerce')
    df['completionYear'] = df['completionDate'].dt.year

# Fill missing categorical values
for col in ['status', 'location', 'componentCategories', 'contractor']:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown")

# Drop missing critical values
df = df.dropna(subset=['infraYear', 'budget'])

# In[5]:
# ===================================================
# INITIALIZE APP
# ===================================================

app = dash.Dash(__name__)
app.title = "Infrastructure Dashboard"
server = app.server  # REQUIRED for deployment

# ===================================================
# KPI CARD FUNCTION
# ===================================================

def kpi_card(title, value, color):
    return html.Div([
        html.H4(title, style={"margin": "0"}),
        html.H2(value, style={"margin": "5px 0"})
    ], style={
        "backgroundColor": color,
        "color": "white",
        "padding": "20px",
        "borderRadius": "12px",
        "boxShadow": "0px 4px 10px rgba(0,0,0,0.1)"
    })

# ===================================================
# LAYOUT
# ===================================================

app.layout = html.Div([

    # ================= HEADER =================
    html.Div([
        html.H1(
            "How does DPWH allocates and manages infrastructure budgets in the Philippines?",
            style={"color": "white", "margin": "0"}
        )
    ], style={
        "backgroundColor": "#111827",
        "padding": "20px"
    }),

    # ================= MAIN SECTION =================
    html.Div([

        # -------- LEFT FILTER PANEL --------
        html.Div([

            html.H3("Filters", style={"color": "white"}),

            dcc.Dropdown(
                id='year-filter',
                options=[{"label": str(y), "value": y}
                         for y in sorted(df['infraYear'].dropna().unique())],
                placeholder="Infra Year",
                clearable=True
            ),

            html.Br(),

            dcc.Dropdown(
                id='completion-year-filter',
                options=[{"label": str(y), "value": y}
                         for y in sorted(df['completionYear'].dropna().unique())],
                placeholder="Completion Year",
                clearable=True
            ),

            html.Br(),

            dcc.Dropdown(
                id='location-filter',
                options=[{"label": l, "value": l}
                         for l in sorted(df['location'].dropna().unique())],
                placeholder="Location",
                multi=True
            ),

            html.Br(),

            dcc.Dropdown(
                id='contractor-filter',
                options=[{"label": c, "value": c}
                         for c in sorted(df['contractor'].dropna().unique())],
                placeholder="Contractor",
                multi=True
            ),

            html.Br(),

            dcc.Dropdown(
                id='component-filter',
                options=[{"label": c, "value": c}
                         for c in sorted(df['componentCategories'].dropna().unique())],
                placeholder="Component Category",
                multi=True
            ),

            html.Br(),

            dcc.Dropdown(
                id='status-filter',
                options=[{"label": s, "value": s}
                         for s in sorted(df['status'].dropna().unique())],
                placeholder="Status",
                multi=True
            ),

        ], style={
            "width": "20%",
            "padding": "20px",
            "backgroundColor": "#1F2937",
            "borderRadius": "10px"
        }),

        # -------- RIGHT CONTENT --------
        html.Div([

            # KPI CARDS
            html.Div(id="kpi-cards", style={
                "display": "grid",
                "gridTemplateColumns": "repeat(3, 1fr)",
                "gap": "15px"
            }),

            html.Br(),

            # CHARTS
            html.Div([
                dcc.Graph(id='combined-chart'),
                dcc.Graph(id='category-chart'),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "20px"
            }),

            html.Br(),

            html.H3("Top 5 Contractors (Sorted by Total Budget)"),

            html.Div(id='contractor-status-table')

        ], style={"width": "80%", "padding": "20px"})

    ], style={"display": "flex"}),

    # ================= FOOTER =================
    html.Div([
        html.Hr(),
        html.P(
            "Data source: Hugging Face dataset 'bettergovph/dpwh-transparency-data', "
            "covering infrastructure data from 2016 to 2026.",
            style={
                "textAlign": "center",
                "fontSize": "14px",
                "color": "#6B7280"
            }
        )
    ], style={"padding": "20px"})

], style={
    "backgroundColor": "#F3F4F6",
    "minHeight": "100vh",
    "fontFamily": "Arial"
})

# ===================================================
# CALLBACK
# ===================================================

@app.callback(
    Output('combined-chart', 'figure'),
    Output('category-chart', 'figure'),
    Output('contractor-status-table', 'children'),
    Output('kpi-cards', 'children'),
    Input('year-filter', 'value'),
    Input('completion-year-filter', 'value'),
    Input('location-filter', 'value'),
    Input('contractor-filter', 'value'),
    Input('component-filter', 'value'),
    Input('status-filter', 'value')
)
def update_dashboard(year, completion_year, location, contractor, component, status):

    filtered_df = df.copy()

    if year:
        filtered_df = filtered_df[filtered_df['infraYear'] == year]

    if completion_year:
        filtered_df = filtered_df[filtered_df['completionYear'] == completion_year]

    if location:
        filtered_df = filtered_df[filtered_df['location'].isin(location)]

    if contractor:
        filtered_df = filtered_df[filtered_df['contractor'].isin(contractor)]

    if component:
        filtered_df = filtered_df[filtered_df['componentCategories'].isin(component)]

    if status:
        filtered_df = filtered_df[filtered_df['status'].isin(status)]

    # ================= TREND CHART =================

    yearly = filtered_df.groupby('infraYear', as_index=False).agg(
        projects=('contractId', 'nunique'),
        budget=('budget', 'sum')
    )

    fig1 = go.Figure()
    fig1.add_bar(x=yearly['infraYear'], y=yearly['projects'], name="Projects")
    fig1.add_scatter(x=yearly['infraYear'], y=yearly['budget'],
                     name="Budget", yaxis="y2")

    fig1.update_layout(
        template="plotly_white",
        title="Yearly Projects and Budget Trend",
        yaxis=dict(title="Projects"),
        yaxis2=dict(title="Budget", overlaying='y', side='right'),
        legend=dict(orientation="h")
    )

    # ================= CATEGORY CHART =================

    category = (
        filtered_df
        .groupby('componentCategories', as_index=False)
        .agg(total_budget=('budget', 'sum'))
        .sort_values("total_budget", ascending=True)
    )

    fig2 = px.bar(
        category,
        x='total_budget',
        y='componentCategories',
        orientation='h',
        title="Total Budget per Component Category"
    )

    fig2.update_layout(template="plotly_white")

    # ================= TOP CONTRACTORS =================

    top_contractors = (
        filtered_df.groupby('contractor')['budget']
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index
    )

    top_df = filtered_df[filtered_df['contractor'].isin(top_contractors)]

    status_table = (
        top_df.groupby(['contractor', 'status'])
        .size()
        .reset_index(name='count')
        .pivot(index='contractor', columns='status', values='count')
        .fillna(0)
        .reset_index()
    )

    budget_table = (
        top_df.groupby('contractor')['budget']
        .sum()
        .reset_index()
        .rename(columns={'budget': 'Total Budget'})
    )

    final_table = status_table.merge(budget_table, on='contractor')
    final_table = final_table.sort_values(by='Total Budget', ascending=False)

    final_table['Total Budget'] = final_table['Total Budget'].apply(
        lambda x: f"₱ {x:,.0f}"
    )

    table_component = dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in final_table.columns],
        data=final_table.to_dict('records'),
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#111827",
            "color": "white",
            "fontWeight": "bold"
        },
        style_cell={"textAlign": "center"},
        page_size=5
    )

    # ================= KPI CARDS =================

    total_budget = filtered_df['budget'].sum()
    total_projects = filtered_df['contractId'].nunique()
    total_status = filtered_df['status'].nunique()

    kpi_cards = [
        kpi_card("Total Budget", f"₱ {total_budget:,.0f}", "#2563EB"),
        kpi_card("Total Projects", f"{total_projects:,.0f}", "#10B981")
    ]

    return fig1, fig2, table_component, kpi_cards

# ===================================================
# RUN APP
# ===================================================

if __name__ == "__main__":
    app.run(debug=False)