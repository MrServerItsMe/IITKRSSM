<!DOCTYPE html>
<html lang="fr">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rayleigh Fast Checker</title>
    <link rel="stylesheet" href="/static/style.css">
</head>

<body>

    <div class="container">

        <header class="top-header">
            <h1>Rayleigh Fast Checker</h1>
            <button class="refresh-btn" onclick="refreshServers()">Refresh Servers</button>
        </header>

        <div class="sort-container">
            <button class="sort-btn" data-sort="initial" onclick="setSort('initial')">Initial</button>
            <button class="sort-btn active" data-sort="event" onclick="setSort('event')">Next Rayleigh</button>
            <button class="sort-btn" data-sort="age" onclick="setSort('age')">Server Age</button>
        </div>

        <main id="servers"></main>

    </div>

    <script src="/static/app.js"></script>

</body>

</html>
