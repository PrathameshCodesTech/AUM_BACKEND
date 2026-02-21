from django.urls import path
from .views import (
    CreateWalletView,
    WalletBalanceView,
    AddFundsView,
    TransactionHistoryView,
    CreateInvestmentView,
    MyInvestmentsView,
    InvestmentDetailView,
    PortfolioAnalyticsView,
    check_cp_relation,
    InvestmentReceiptsView,
    DownloadReceiptView,
    ReceiptDetailView,
    # Instalment payment views
    PayRemainingView,
    InvestmentPaymentsListView,
    DownloadPaymentReceiptView,
)

app_name = 'investments'

urlpatterns = [
    # Wallet APIs
    path('create/', CreateWalletView.as_view(), name='wallet-create'),
    path('balance/', WalletBalanceView.as_view(), name='wallet-balance'),
    path('add-funds/', AddFundsView.as_view(), name='add-funds'),
    path('transactions/', TransactionHistoryView.as_view(), name='transactions'),
    path('investments/create/', CreateInvestmentView.as_view(), name='create-investment'),
    path('investments/my-investments/', MyInvestmentsView.as_view(), name='my-investments'),
    path('investments/<int:investment_id>/details/', InvestmentDetailView.as_view(), name='investment-detail'),
    path('investments/portfolio/analytics/', PortfolioAnalyticsView.as_view(), name='portfolio-analytics'),
    path('investments/check-cp-relation/', check_cp_relation, name='check-cp-relation'),

       # Receipt APIs (User Side)
    path('investments/receipts/', InvestmentReceiptsView.as_view(), name='investment-receipts'),
    path('investments/<int:investment_id>/receipt/', ReceiptDetailView.as_view(), name='receipt-detail'),
    path('investments/<int:investment_id>/receipt/download/', DownloadReceiptView.as_view(), name='receipt-download'),

    # Instalment / Pay-Remaining APIs
    path('investments/<int:investment_id>/pay-remaining/', PayRemainingView.as_view(), name='pay-remaining'),
    path('investments/<int:investment_id>/payments/', InvestmentPaymentsListView.as_view(), name='investment-payments'),
    path('investments/<int:investment_id>/payments/<int:payment_id>/receipt/download/', DownloadPaymentReceiptView.as_view(), name='payment-receipt-download'),
]