# Uni-App Mini Program Tooling

Use this reference when actual HBuilderX or WeChat DevTools execution is needed.

## HBuilderX

- First inspect whether HBuilderX CLI is installed or documented in the local project setup.
- On Windows, common installations may expose a `cli.exe` under the HBuilderX installation directory, but paths vary.
- Run the discovered executable with help output before assuming commands.
- Use HBuilderX to compile or run `wellness_uniapp` when available.

If CLI is unavailable, ask the user to open the project in HBuilderX and provide compile output, or provide a manual checklist.

## WeChat DevTools CLI

- Check whether WeChat DevTools CLI is installed or available on `PATH`.
- CLI names and flags differ by version; run help first.
- Use CLI for project open, compile/build checks, preview QR generation, or automation only when supported by the installed version.
- Use DevTools Network, Console, and compile logs to verify API calls and runtime errors.

Do not upload, submit review, or change AppID without explicit user confirmation.

## Evidence To Capture

- command and result
- page path
- console error
- network request and response summary
- screenshot path
- manual blocker reason
