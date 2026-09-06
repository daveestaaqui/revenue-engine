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

        const isBugReport = department.toLowerCase().includes('bug') || body.category === 'System Bug Report';
        const safeName = (name || (isBugReport ? 'Platform Bug Reporter' : '')).trim();
        const safeEmail = (email || (isBugReport ? 'inquiries@surplusdocket.com' : '')).trim();

        // Verify required fields
        if (!safeName || !safeEmail || !message) {
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
            `Name / Counsel:  ${safeName}`,
            `Direct Email:    ${safeEmail}`,
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

        const escapeHtml = (str) => String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

        // Executive HTML layout
        const htmlMemo = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f8f4; margin: 0; padding: 24px 8px; color: #1e293b; }
        .container { max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 16px -2px rgba(0,0,0,0.05); }
        .header { background: #ffffff; padding: 20px 32px; border-bottom: 2px solid #1b365d; display: flex; align-items: center; justify-content: space-between; }
        .brand-wrap { display: flex; align-items: center; gap: 12px; }
        .brand-title { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 22px; font-weight: 900; letter-spacing: -0.02em; margin: 0; line-height: 1.15; }
        .brand-sub { margin: 2px 0 0 0; font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
        .badge-pill { display: inline-block; background: #edf3ec; border: 1px solid #c2d9c0; color: #365134; font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 9999px; }
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
            <div class="brand-wrap">
                <img src="https://surplusdocket.com/assets/logo_surplus_docket.png" alt="Surplus Docket Crest" width="40" height="32" style="display: block; width: 40px; height: auto;" />
                <div>
                    <div class="brand-title"><span style="color: #4c6d48;">SURPLUS</span> <span style="color: #1b365d;">DOCKET</span></div>
                    <p class="brand-sub">Official Statutory Correspondence Memorandum</p>
                </div>
            </div>
            <span class="badge-pill">TRANSMISSION</span>
        </div>
        <div class="content">
            <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                <span class="ref-pill">${escapeHtml(reference_number)}</span>
                <span style="font-size: 12px; color: #64748b;">${dateStr}</span>
            </div>
            <table class="meta-grid">
                <tr>
                    <td class="label">Counsel / Name</td>
                    <td class="value">${escapeHtml(safeName)}</td>
                </tr>
                <tr>
                    <td class="label">Direct Email</td>
                    <td class="value"><a href="mailto:${escapeHtml(safeEmail)}" style="color: #1b365d; text-decoration: underline;">${escapeHtml(safeEmail)}</a></td>
                </tr>
                <tr>
                    <td class="label">Firm / Organization</td>
                    <td class="value">${escapeHtml(firm || 'None Specified')}</td>
                </tr>
                <tr>
                    <td class="label">Jurisdiction</td>
                    <td class="value">${escapeHtml(jurisdiction)}</td>
                </tr>
                <tr>
                    <td class="label">Inquiry Category</td>
                    <td class="value">${escapeHtml(department)}</td>
                </tr>
                <tr>
                    <td class="label">Docket / Parcel ID</td>
                    <td class="value font-mono">${escapeHtml(docket_or_parcel)}</td>
                </tr>
            </table>

            <div class="memo-box">
                <h3>Statement of Inquiry</h3>
                <p>${escapeHtml(message)}</p>
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
            const recipient = env.INQUIRY_RECIPIENT || 'elena.brooks@surplusdocket.com';
            const fromSender = env.RESEND_FROM || 'Surplus Docket Inquiries <inquiries@surplusdocket.com>';

            const resendRes = await fetch('https://api.resend.com/emails', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${env.RESEND_API_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    from: fromSender,
                    to: [recipient],
                    reply_to: safeEmail,
                    subject: `[Surplus Docket Inquiry] ${department} — ${firm || 'Direct'} (${safeName})`,
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
