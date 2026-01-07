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
                                        <a href="https://qnt9.com/stock/{{ symbol }}" 
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
                                <a href="https://qnt9.com/settings" style="color: #667eea; text-decoration: none;">Manage your notification preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
                
                <table width="600" cellpadding="0" cellspacing="0" style="margin-top: 20px;">
                    <tr>
                        <td align="center">
                            <p style="font-size: 12px; color: #999; margin: 0;">
                                QNT9 Stock Research Platform
                                <br>
                                <a href="https://qnt9.com" style="color: #667eea; text-decoration: none;">qnt9.com</a>
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
    <title>Welcome to QNT9</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 32px;">Welcome to QNT9</h1>
                            <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 16px;">Stock Research Platform</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                {% if user_name %}Hello {{ user_name }},{% else %}Hello,{% endif %}
                            </p>
                            <p style="font-size: 16px; margin-bottom: 20px;">
                                Thank you for joining QNT9, your intelligent stock research platform powered by advanced analytics and AI.
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
                                        <a href="https://qnt9.com/search" 
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
                                Questions? Visit our <a href="https://qnt9.com/docs" style="color: #667eea; text-decoration: none;">documentation</a> or contact support.
                                <br>
                                <a href="https://qnt9.com/settings" style="color: #667eea; text-decoration: none;">Manage email preferences</a>
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
                                <a href="https://qnt9.com/settings" style="color: #667eea; text-decoration: none;">Manage email preferences</a>
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
