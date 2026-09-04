// Cloudflare Pages Function: /api/inquiry
// Handles practitioner and subscriber inquiries with zero third-party ads or sponsor branding

export async function onRequestPost(context) {
    const { request, env } = context;

    try {
        const body = await request.json();
        const {
            name = '',
            email = '',
            firm = 'Independent Practice',
            jurisdiction = 'All Jurisdictions',
            department = 'General Inquiry',
            docket_or_parcel = 'Not Specified',
            message = '',
            reference_number = `SD-INQ-${Date.now()}`
        } = body;

        // Verify required fields
        if (!name || !email || !message) {
            return new Response(JSON.stringify({ error: 'Missing required inquiry parameters.' }), {
                status: 400,
                headers: { 'Content-Type': 'application/json' }
            });
        }

        const dateStr = new Date().toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            timeZone: 'America/New_York'
        });

        const timeStr = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short',
            timeZone: 'America/New_York'
        });

        // Structured plain text memorandum (clean format for quoting upon reply)
        const textMemo = [
            `================================================================================`,
            `SURPLUS DOCKET — LEGAL & STATUTORY CORRESPONDENCE MEMORANDUM`,
            `Tracking Ref:    ${reference_number}`,
            `Filed:           ${dateStr} at ${timeStr}`,
            `================================================================================`,
            ``,
            `TRANSMITTING PRACTITIONER / PARTY:`,
            `--------------------------------------------------------------------------------`,
            `Name / Counsel:  ${name}`,
            `Direct Email:    ${email}`,
            `Firm / Org:      ${firm}`,
            `Jurisdiction:    ${jurisdiction}`,
            `Department:      ${department}`,
            `Docket / Parcel: ${docket_or_parcel}`,
            ``,
            `STATEMENT OF INQUIRY:`,
            `--------------------------------------------------------------------------------`,
            message,
            ``,
            `================================================================================`,
            `Surplus Docket Editorial & Statutory Compliance Desk | https://surplusdocket.com`,
            `Confidential Practitioner Transmission — Attorney-Client / Regulatory Privilege`,
            `================================================================================`
        ].join('\n');

        // Executive HTML layout
        const htmlMemo = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 24px; color: #1e293b; }
        .container { max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        .header { background: #1b365d; padding: 24px 32px; border-bottom: 3px solid #4c6d48; }
        .header h1 { margin: 0; font-size: 20px; font-weight: 800; letter-spacing: -0.02em; color: #ffffff; }
        .header p { margin: 6px 0 0 0; font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; font-family: monospace; }
        .content { padding: 32px; }
        .meta-grid { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
        .meta-grid td { padding: 8px 12px; font-size: 13px; border-bottom: 1px solid #f1f5f9; }
        .meta-grid td.label { font-weight: 600; color: #64748b; width: 140px; background: #f8fafc; }
        .meta-grid td.value { color: #0f172a; font-weight: 500; }
        .memo-box { background: #f8fafc; border-left: 4px solid #4c6d48; padding: 16px 20px; border-radius: 0 8px 8px 0; margin-top: 16px; }
        .memo-box h3 { margin: 0 0 10px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; }
        .memo-box p { margin: 0; font-size: 14px; line-height: 1.6; color: #1e293b; white-space: pre-wrap; font-family: monospace; }
        .footer { background: #f8fafc; padding: 16px 32px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }
        .ref-pill { display: inline-block; background: #edf3ec; color: #365134; font-family: monospace; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SURPLUS DOCKET</h1>
            <p>Official Statutory Correspondence Memorandum</p>
        </div>
        <div class="content">
            <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                <span class="ref-pill">${reference_number}</span>
                <span style="font-size: 12px; color: #64748b;">${dateStr}</span>
            </div>
            <table class="meta-grid">
                <tr>
                    <td class="label">Counsel / Name</td>
                    <td class="value">${name}</td>
                </tr>
                <tr>
                    <td class="label">Direct Email</td>
                    <td class="value"><a href="mailto:${email}" style="color: #1b365d; text-decoration: underline;">${email}</a></td>
                </tr>
                <tr>
                    <td class="label">Firm / Organization</td>
                    <td class="value">${firm || 'None Specified'}</td>
                </tr>
                <tr>
                    <td class="label">Jurisdiction</td>
                    <td class="value">${jurisdiction}</td>
                </tr>
                <tr>
                    <td class="label">Inquiry Category</td>
                    <td class="value">${department}</td>
                </tr>
                <tr>
                    <td class="label">Docket / Parcel ID</td>
                    <td class="value font-mono">${docket_or_parcel}</td>
                </tr>
            </table>

            <div class="memo-box">
                <h3>Statement of Inquiry</h3>
                <p>${message.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
            </div>
        </div>
        <div class="footer">
            Surplus Docket • Public Records Compiler • Not a Law Firm • Transmitted securely via Cloudflare Pages
        </div>
    </div>
</body>
</html>`;

        // If RESEND_API_KEY is configured in Cloudflare Pages environment variables, deliver directly via Resend
        if (env && env.RESEND_API_KEY) {
            const recipient = env.INQUIRY_RECIPIENT || 'david@surplusdocket.com';
            const fromSender = env.RESEND_FROM || 'Surplus Docket <inquiries@surplusdocket.com>';

            const resendRes = await fetch('https://api.resend.com/emails', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${env.RESEND_API_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    from: fromSender,
                    to: [recipient],
                    reply_to: email,
                    subject: `[Surplus Docket Inquiry] ${department} — ${firm || 'Direct'} (${name})`,
                    text: textMemo,
                    html: htmlMemo
                })
            });

            if (resendRes.ok) {
                return new Response(JSON.stringify({ success: true, reference: reference_number, channel: 'direct' }), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' }
                });
            } else {
                const errData = await resendRes.text();
                console.error('Resend delivery error:', errData);
            }
        }

        // Return signal to client that direct delivery isn't configured so client uses formatted FormSubmit fallback
        return new Response(JSON.stringify({
            success: false,
            fallback: true,
            memo: textMemo,
            reference: reference_number
        }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });

    } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
