// Cloudflare Pages Function: /api/stripe-webhook
// Handles real-time Stripe checkout and subscription events for autonomous subscriber intake
// Includes cryptographic HMAC-SHA256 signature verification via Web Crypto API

/**
 * Cryptographically verify Stripe webhook signature using Web Crypto API.
 * Follows Stripe signature specification (t=timestamp,v1=signature).
 */
async function verifyStripeSignature(payload, signatureHeader, secret, toleranceSeconds = 300) {
    if (!signatureHeader || !secret) {
        return false;
    }

    const items = signatureHeader.split(',');
    let timestamp = null;
    const signatures = [];

    for (const item of items) {
        const [k, v] = item.split('=');
        if (k === 't') {
            timestamp = parseInt(v, 10);
        } else if (k === 'v1') {
            signatures.push(v);
        }
    }

    if (!timestamp || signatures.length === 0 || isNaN(timestamp)) {
        return false;
    }

    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - timestamp) > toleranceSeconds) {
        console.warn(`Stripe webhook signature timestamp rejected (skew: ${Math.abs(now - timestamp)}s)`);
        return false;
    }

    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
        'raw',
        encoder.encode(secret),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
    );

    const signedData = encoder.encode(`${timestamp}.${payload}`);
    const signatureBuffer = await crypto.subtle.sign('HMAC', key, signedData);
    const hashArray = Array.from(new Uint8Array(signatureBuffer));
    const computedSignature = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    // Constant-time comparison
    return signatures.some(sig => {
        if (sig.length !== computedSignature.length) return false;
        let diff = 0;
        for (let i = 0; i < sig.length; i++) {
            diff |= sig.charCodeAt(i) ^ computedSignature.charCodeAt(i);
        }
        return diff === 0;
    });
}

export async function onRequestPost(context) {
    const { request, env } = context;

    try {
        const payload = await request.text();

        // Verify cryptographic signature if secret is configured in environment
        if (env && env.STRIPE_WEBHOOK_SECRET) {
            const signatureHeader = request.headers.get('stripe-signature');
            const isValid = await verifyStripeSignature(payload, signatureHeader, env.STRIPE_WEBHOOK_SECRET);
            if (!isValid) {
                console.error('Invalid or unverified Stripe webhook signature.');
                return new Response(JSON.stringify({ error: 'Invalid webhook signature.' }), {
                    status: 401,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
        }

        const event = JSON.parse(payload);
        const eventType = event.type;
        console.log(`Received verified Stripe event: ${eventType}`);

        let customerEmail = null;
        let customerName = 'Counsel';
        let tier = 'Core Plan (7-Day Evaluation)';
        let action = null;

        if (eventType === 'checkout.session.completed') {
            const session = event.data?.object || {};
            customerEmail = session.customer_details?.email || session.customer_email;
            customerName = session.customer_details?.name || 'Counsel';
            tier = session.metadata?.tier || (session.amount_total >= 40000 ? 'Six-State National Feed + REST API' : 'Core Plan (7-Day Evaluation)');
            action = 'add';
        } else if (eventType === 'customer.subscription.created' || eventType === 'customer.subscription.updated') {
            const sub = event.data?.object || {};
            customerEmail = sub.customer_email || sub.metadata?.email;
            tier = sub.metadata?.tier || 'Core Plan (7-Day Evaluation)';

            // Fetch customer email from Stripe Customer API if absent on Subscription object
            if (!customerEmail && sub.customer && env && env.STRIPE_API_KEY) {
                try {
                    const custRes = await fetch(`https://api.stripe.com/v1/customers/${sub.customer}`, {
                        headers: { 'Authorization': `Bearer ${env.STRIPE_API_KEY}` }
                    });
                    if (custRes.ok) {
                        const custData = await custRes.json();
                        customerEmail = custData.email;
                        customerName = custData.name || customerName;
                    }
                } catch (e) {
                    console.error('Failed to resolve customer email on subscription created:', e);
                }
            }
            action = 'add';
        } else if (eventType === 'customer.subscription.deleted') {
            const sub = event.data?.object || {};
            customerEmail = sub.customer_email || sub.metadata?.email;

            // Fetch customer email from Stripe Customer API if absent on Subscription object
            if (!customerEmail && sub.customer && env && env.STRIPE_API_KEY) {
                try {
                    const custRes = await fetch(`https://api.stripe.com/v1/customers/${sub.customer}`, {
                        headers: { 'Authorization': `Bearer ${env.STRIPE_API_KEY}` }
                    });
                    if (custRes.ok) {
                        const custData = await custRes.json();
                        customerEmail = custData.email;
                    }
                } catch (e) {
                    console.error('Failed to resolve customer email on subscription deleted:', e);
                }
            }
            action = 'deactivate';
        }

        // If GITHUB_TOKEN is configured in Cloudflare Pages, dispatch to repository workflow
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
                        tier: tier
                    }
                })
            });
        }

        return new Response(JSON.stringify({ received: true, event: eventType, email_resolved: !!customerEmail }), {
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
