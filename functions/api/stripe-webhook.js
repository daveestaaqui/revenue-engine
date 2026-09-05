// Cloudflare Pages Function: /api/stripe-webhook
// Handles real-time Stripe checkout and subscription events for autonomous subscriber intake

export async function onRequestPost(context) {
    const { request, env } = context;

    try {
        const payload = await request.text();
        const event = JSON.parse(payload);

        const eventType = event.type;
        console.log(`Received Stripe event: ${eventType}`);

        let customerEmail = null;
        let customerName = 'Counsel';
        let action = null;

        if (eventType === 'checkout.session.completed') {
            const session = event.data?.object || {};
            customerEmail = session.customer_details?.email || session.customer_email;
            customerName = session.customer_details?.name || 'Counsel';
            action = 'add';
        } else if (eventType === 'customer.subscription.created') {
            const sub = event.data?.object || {};
            customerEmail = sub.customer_email || sub.metadata?.email;
            action = 'add';
        } else if (eventType === 'customer.subscription.deleted') {
            const sub = event.data?.object || {};
            customerEmail = sub.customer_email || sub.metadata?.email;
            action = 'deactivate';
        }

        // If GITHUB_TOKEN is configured in Cloudflare Pages, dispatch to repository
        if (customerEmail && action && env && env.GITHUB_TOKEN) {
            const repoOwner = env.GITHUB_REPO_OWNER || 'daveestaaqui';
            const repoName = env.GITHUB_REPO_NAME || 'revenue-engine';
            
            await fetch(`https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/manage_subscribers.yml/dispatches`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Surplus-Docket-Stripe-Webhook',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ref: 'main',
                    inputs: {
                        action: action,
                        email: customerEmail,
                        name: customerName,
                        firm: 'Legal Practice',
                        tier: 'Core Plan (7-Day Evaluation)'
                    }
                })
            });
        }

        return new Response(JSON.stringify({ received: true, event: eventType }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });

    } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
