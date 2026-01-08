PRICE_ALERT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Price Alert</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Price Alert Triggered</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                {% if user_name %}Hello {{ user_name }},{% else %}Hello,{% endif %}
                            </p>
                            <p style="font-size: 16px; margin-bottom: 30px;">
                                Your price alert for <strong>{{ symbol }}</strong> has been triggered.
                            </p>
                            
                            <table width="100%" style="background-color: #f8f9fa; border-radius: 6px; padding: 20px; margin-bottom: 30px;">
                                <tr>
                                    <td style="padding: 10px;">
                                        <strong style="display: block; color: #666; font-size: 14px; margin-bottom: 5px;">Symbol</strong>
                                        <span style="font-size: 24px; color: #333; font-weight: bold;">{{ symbol }}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px;">
                                        <strong style="display: block; color: #666; font-size: 14px; margin-bottom: 5px;">Current Price</strong>
                                        <span style="font-size: 32px; color: {% if direction == 'above' %}#10b981{% else %}#ef4444{% endif %}; font-weight: bold;">
                                            ${{ "%.2f"|format(current_price) }}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px;">
                                        <strong style="display: block; color: #666; font-size: 14px; margin-bottom: 5px;">Alert Threshold</strong>
                                        <span style="font-size: 18px; color: #333;">
                                            {% if direction == 'above' %}Above{% else %}Below{% endif %} ${{ "%.2f"|format(threshold_price) }}
                                        </span>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 14px; color: #666; margin-bottom: 30px;">
                                This alert is sent once every 24 hours while the condition is met.
                            </p>

                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <a href="https://finio.cloud/stock/{{ symbol }}" 
                                           style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 12px 30px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                                            View Stock Details
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px;">
                            <p style="font-size: 12px; color: #666; margin: 0; text-align: center;">
                                You are receiving this email because you have price alerts enabled for {{ symbol }}.
                                <br>
                                <a href="https://finio.cloud/settings" style="color: #667eea; text-decoration: none;">Manage your notification preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
                
                <table width="600" cellpadding="0" cellspacing="0" style="margin-top: 20px;">
                    <tr>
                        <td align="center">
                            <p style="font-size: 12px; color: #999; margin: 0;">
                                Finio Stock Research Platform
                                <br>
                                <a href="https://finio.cloud" style="color: #667eea; text-decoration: none;">finio.cloud</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

MARKETING_WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Finio</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 32px;">Welcome to Finio</h1>
                            <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 16px;">Stock Research Platform</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                {% if user_name %}Hello {{ user_name }},{% else %}Hello,{% endif %}
                            </p>
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                Thank you for joining Finio, your intelligent stock research platform powered by advanced analytics and AI.
                            </p>
                            
                            <h2 style="color: #667eea; font-size: 20px; margin: 30px 0 20px 0;">Get Started</h2>
                            
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                                <tr>
                                    <td style="padding: 15px; background-color: #f8f9fa; border-radius: 6px; margin-bottom: 10px;">
                                        <strong style="color: #667eea; font-size: 16px;">1. Search Stocks</strong>
                                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                                            Use our powerful search to find and analyze stocks
                                        </p>
                                    </td>
                                </tr>
                                <tr><td style="height: 10px;"></td></tr>
                                <tr>
                                    <td style="padding: 15px; background-color: #f8f9fa; border-radius: 6px; margin-bottom: 10px;">
                                        <strong style="color: #667eea; font-size: 16px;">2. Create Watchlists</strong>
                                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                                            Track your favorite stocks and set price alerts
                                        </p>
                                    </td>
                                </tr>
                                <tr><td style="height: 10px;"></td></tr>
                                <tr>
                                    <td style="padding: 15px; background-color: #f8f9fa; border-radius: 6px;">
                                        <strong style="color: #667eea; font-size: 16px;">3. Get Insights</strong>
                                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                                            Receive daily summaries and AI-powered analysis
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px;">
                                <tr>
                                    <td align="center">
                                        <a href="https://finio.cloud/search" 
                                           style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 35px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                                            Start Exploring
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px;">
                            <p style="font-size: 12px; color: #666; margin: 0; text-align: center;">
                                Questions? Visit our <a href="https://finio.cloud/docs" style="color: #667eea; text-decoration: none;">documentation</a> or contact support.
                                <br>
                                <a href="https://finio.cloud/settings" style="color: #667eea; text-decoration: none;">Manage email preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

PRODUCT_UPDATE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Product Update</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px;">{{ title|default("Product Update") }}</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                {% if user_name %}Hello {{ user_name }},{% else %}Hello,{% endif %}
                            </p>
                            
                            <div style="font-size: 16px; line-height: 1.8;">
                                {{ content|safe }}
                            </div>

                            {% if cta_text and cta_url %}
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px;">
                                <tr>
                                    <td align="center">
                                        <a href="{{ cta_url }}" 
                                           style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 12px 30px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                                            {{ cta_text }}
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            {% endif %}
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px;">
                            <p style="font-size: 12px; color: #666; margin: 0; text-align: center;">
                                You are receiving this email because you subscribed to product updates.
                                <br>
                                <a href="https://finio.cloud/settings" style="color: #667eea; text-decoration: none;">Manage email preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


DAILY_SUMMARY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Stock Summary</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Daily Stock Summary</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">{{ summary_date }}</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                {% if user_name %}Good morning {{ user_name }},{% else %}Good morning,{% endif %}
                            </p>
                            <p style="font-size: 16px; margin-bottom: 30px;">
                                Here is your daily summary for your watchlist stocks.
                            </p>

                            {% if stocks and stocks|length > 0 %}
                            <h2 style="color: #333; font-size: 18px; margin: 30px 0 15px 0; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                                Your Watchlist
                            </h2>
                            
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px;">
                                <tr style="background-color: #f8f9fa;">
                                    <th style="padding: 12px 10px; text-align: left; font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase;">Symbol</th>
                                    <th style="padding: 12px 10px; text-align: right; font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase;">Price</th>
                                    <th style="padding: 12px 10px; text-align: right; font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase;">Change</th>
                                </tr>
                                {% for stock in stocks %}
                                {% if stock.quote %}
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 15px 10px;">
                                        <a href="https://finio.cloud/stock/{{ stock.symbol }}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 16px;">{{ stock.symbol }}</a>
                                    </td>
                                    <td style="padding: 15px 10px; text-align: right; font-size: 16px; font-weight: 500;">
                                        ${{ "%.2f"|format(stock.quote.current_price) }}
                                    </td>
                                    <td style="padding: 15px 10px; text-align: right; font-size: 14px; font-weight: 500; color: {% if stock.quote.change >= 0 %}#10b981{% else %}#ef4444{% endif %};">
                                        {% if stock.quote.change >= 0 %}+{% endif %}{{ "%.2f"|format(stock.quote.change) }} ({% if stock.quote.change_percent >= 0 %}+{% endif %}{{ "%.2f"|format(stock.quote.change_percent) }}%)
                                    </td>
                                </tr>
                                {% endif %}
                                {% endfor %}
                            </table>

                            <h2 style="color: #333; font-size: 18px; margin: 30px 0 15px 0; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                                Latest News
                            </h2>
                            
                            {% for stock in stocks %}
                            {% if stock.news and stock.news|length > 0 %}
                            <div style="margin-bottom: 25px;">
                                <h3 style="color: #667eea; font-size: 16px; margin: 0 0 12px 0;">{{ stock.symbol }}</h3>
                                {% for news_item in stock.news[:3] %}
                                <div style="margin-bottom: 12px; padding-left: 15px; border-left: 3px solid #667eea;">
                                    <a href="{{ news_item.url }}" style="color: #333; text-decoration: none; font-size: 14px; font-weight: 500; line-height: 1.4;">
                                        {{ news_item.title }}
                                    </a>
                                    {% if news_item.source %}
                                    <p style="margin: 4px 0 0 0; font-size: 12px; color: #666;">{{ news_item.source }}{% if news_item.published_at %} - {{ news_item.published_at }}{% endif %}</p>
                                    {% endif %}
                                </div>
                                {% endfor %}
                            </div>
                            {% endif %}
                            {% endfor %}
                            {% else %}
                            <div style="text-align: center; padding: 40px 20px; background-color: #f8f9fa; border-radius: 6px;">
                                <p style="color: #666; font-size: 16px; margin: 0;">
                                    No stocks in your watchlist yet.
                                </p>
                                <a href="https://finio.cloud/search" style="display: inline-block; margin-top: 15px; color: #667eea; text-decoration: none; font-weight: 500;">
                                    Search for stocks to add
                                </a>
                            </div>
                            {% endif %}

                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 30px;">
                                <tr>
                                    <td align="center">
                                        <a href="https://finio.cloud/watchlist" 
                                           style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 12px 30px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                                            View Full Watchlist
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px;">
                            <p style="font-size: 12px; color: #666; margin: 0; text-align: center;">
                                You are receiving this email because you have daily stock summaries enabled.
                                <br>
                                <a href="https://finio.cloud/settings" style="color: #667eea; text-decoration: none;">Manage your notification preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
                
                <table width="600" cellpadding="0" cellspacing="0" style="margin-top: 20px;">
                    <tr>
                        <td align="center">
                            <p style="font-size: 12px; color: #999; margin: 0;">
                                Finio Stock Research Platform
                                <br>
                                <a href="https://finio.cloud" style="color: #667eea; text-decoration: none;">finio.cloud</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
