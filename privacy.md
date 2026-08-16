# Hornet Privacy Policy

Hornet is a private bot used exclusively for the moderation of the Hollow Knight Speedrun & Racing Community's servers. Data described below is used exclusively for the fulfilment of moderation features in the Hollow Knight Speedrun & Racing Community server. Hornet is Free & Open Source Software; code is provided under LGPLv2.1 at https://github.com/ManicJamie/HornetBot.

Hornet does not collect any end-user data; all data stored is used exclusively for configuration by server & bot moderators.

Hornet does not process or store your Discord data outside of when it is required to provide a command or repeated task; this includes the following:
- The content of your messages is read to detect the command prefix; message content is discarded immediately after the command is processed.
- Hornet may access your server membership data only when using `grantsrrole` & certain moderation commands, which it uses to detect & update your roles as necessary. This data is not stored.
- Moderators can configure Hornet to use certain features, which requires storing data. This data is limited to:
    - Guild, Role & Message Ids are stored to process reaction roles, SRC queue verification, moderation features & per-server logging.
    - A list of custom command names & outputs defined by server moderators, used for FAQs (often referred to as 'tags' in more modern bots).
    - String IDs for community Speedrun.com API data, used for Hornet's Speedrun.com integrations.
- Hornet may log errors in order to improve the service; this may include certain user data described in this document if a command errors

Hornet obtains some publically available data using Speedrun.com's API. This is in full compliance with Speedrun.com's terms of use, and limited to the following features:
- The `grantsrrole` command uses the Speedrun.com username you provide to look up your Speedrun.com profile data, to verify the profile is connected to your Discord account & has a verified run in a valid game, to provide you with verified runner roles.
    - This data is discarded as soon as Hornet provides a response to your command.
- Hornet's run queue autoformatting system reads from Speedrun.com's API and automatically edits runs to follow some rules. 
    - This data is limited to public data runners provide as part of their submission to Speedrun.com, and is provided by Speedrun.com under a CC-NC-4.0 license; this includes your submissions' ID, run time, URL to video evidence, and run description.
    - Hornet may edit this data in accordance with permissions provided to game moderators by Speedrun.com. A summary of edits will be added to the run's public description, and logged to a moderation channel for monitoring purposes.
    - Hornet does not store any of this data except the run ID, which is stored for 30 days to prevent duplicate edits.
- Hornet's run queue tracking reads from Speedrun.com's API and posts unverified runs to a queue channel for verification queue tracking.
    - This data is limited to public data runners provide as part of their submission to Speedrun.com, and is provided by Speedrun.com under a CC-NC-4.0 license; this includes your submissions' ID, run time, url to video evidence, and run description.
    - Hornet posts a limited subset of this data to a Discord channel for the duration of your run's time in the verification queue, limited to game, category, level & time information, as well as a URL to the submission.
    - Once your run is verified, all run data is deleted except the run ID, which is stored for 30 days to prevent duplicate & out-of-order entries being added to the queue. After 30 days, this ID is also removed.

If you wish to request removal of your data, you may email hornet@manicjamie.com with your request.