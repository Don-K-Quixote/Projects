import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from sklearn.metrics import confusion_matrix

# Initialize Dash app
app = dash.Dash(__name__)

# Load data
rf_importance = pd.read_csv('rf_feature_importance.csv')
xgb_importance = pd.read_csv('xgb_feature_importance.csv')
performance = pd.read_csv('model_performance.csv')
predictions_df = pd.read_csv('dropout_predictions.csv')

# Generate confusion matrices for both models
rf_conf_matrix = confusion_matrix(predictions_df['Actual Dropout'], predictions_df['Random Forest Prediction'])
xgb_conf_matrix = confusion_matrix(predictions_df['Actual Dropout'], predictions_df['XGBoost Prediction'])

# Create a plotly figure for the confusion matrix
def plot_confusion_matrix(cm, model_name):
    fig = ff.create_annotated_heatmap(
        z=cm,
        x=['Predicted No Dropout', 'Predicted Dropout'],
        y=['Actual No Dropout', 'Actual Dropout'],
        colorscale='Viridis',
        colorbar_title='Count',
    )
    fig.update_layout(
        title=f'{model_name} Confusion Matrix',
        xaxis_title='Predicted',
        yaxis_title='Actual',
    )
    return fig

# Create confusion matrix figures for both models
rf_conf_matrix_fig = plot_confusion_matrix(rf_conf_matrix, "Random Forest")
xgb_conf_matrix_fig = plot_confusion_matrix(xgb_conf_matrix, "XGBoost")

# App Layout
app.layout = html.Div([
    html.H1("Clinical Trial Optimization Dashboard", style={'textAlign': 'center'}),

    # Model Performance
    html.H2("Model Performance"),
    dcc.Graph(
        id='model-performance',
        figure=px.bar(performance, x='Model', y='Accuracy', color='Model', title='Model Accuracy')
    ),

    # Feature Importance Dropdown
    html.H2("Feature Importance"),
    dcc.Dropdown(
        id='model-dropdown',
        options=[
            {'label': 'Random Forest', 'value': 'rf'},
            {'label': 'XGBoost', 'value': 'xgb'}
        ],
        value='rf'
    ),
    dcc.Graph(id='feature-importance'),

    # Dropout Predictions Overview
    html.H2("Dropout Predictions Overview"),
    dcc.Dropdown(
        id='prediction-model-dropdown',
        options=[
            {'label': 'Random Forest', 'value': 'Random Forest Prediction'},
            {'label': 'XGBoost', 'value': 'XGBoost Prediction'}
        ],
        value='Random Forest Prediction'
    ),
    dcc.Graph(id='dropout-predictions'),

    # Confusion Matrix Section
    html.H2("Confusion Matrix"),
    dcc.Dropdown(
        id='confusion-matrix-dropdown',
        options=[
            {'label': 'Random Forest', 'value': 'Random Forest'},
            {'label': 'XGBoost', 'value': 'XGBoost'}
        ],
        value='Random Forest'
    ),
    dcc.Graph(id='confusion-matrix')
])

# Callback to update feature importance graph
@app.callback(
    Output('feature-importance', 'figure'),
    [Input('model-dropdown', 'value')]
)
def update_feature_importance(selected_model):
    if selected_model == 'rf':
        fig = px.bar(rf_importance, x='Importance', y='Feature', orientation='h', title='Random Forest - Feature Importance')
    else:
        fig = px.bar(xgb_importance, x='Importance', y='Feature', orientation='h', title='XGBoost - Feature Importance')
    
    return fig

# Callback to update dropout predictions graph
@app.callback(
    Output('dropout-predictions', 'figure'),
    [Input('prediction-model-dropdown', 'value')]
)
def update_dropout_predictions(selected_model):
    # Group by actual and predicted values
    predictions_count = predictions_df.groupby(['Actual Dropout', selected_model]).size().reset_index(name='Count')

    # Plot predictions
    fig = px.bar(predictions_count,
                 x='Actual Dropout',
                 y='Count',
                 color=selected_model,
                 barmode='group',
                 title='Actual vs Predicted Dropouts')

    return fig

# Callback to update confusion matrix
@app.callback(
    Output('confusion-matrix', 'figure'),
    [Input('confusion-matrix-dropdown', 'value')]
)
def update_confusion_matrix(selected_model):
    if selected_model == 'Random Forest':
        return rf_conf_matrix_fig
    else:
        return xgb_conf_matrix_fig

# Run app
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)

