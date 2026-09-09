<% if (ctx.canInspire) { %>
    <% if (ctx.onCooldown) { %>
        <a class='inspire inactive' title='<%- ctx.cooldownMessage %>'>
            <i class='fa fa-star'></i>
    <% } else { %>
        <a href class='inspire'>
            <i class='fa fa-star-o'></i>
    <% } %>
<% } else { %>
    <a class='inspire inactive'>
        <i class='fa fa-star-o'></i>
<% } %>
    <span class='vim-nav-hint'>inspire</span>
</a>
<span class='value'><%- ctx.inspirationCount %></span>
