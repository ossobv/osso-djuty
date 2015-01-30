// vim: set ts=8 sw=4 sts=4 et ai:

if (!window.osso)
    window.osso = {};

if (!window.osso.userchat) {
    // Constructor
    var Channel = function(userchat_url, input_field, output_field, multichannelquery, channel_id) {
        this.userchat_url = userchat_url; // default: "/im/<channel_id>/"
        this.input_field = input_field;
        this.output_field = output_field;
        // multichannelquery and channel_id are optional
        this.last_message_id = 0; // 0 is safe

        var that = this;

        // Trap the enter key
        $(this.input_field).keypress(function(ev) {
            if (ev.keyCode == 13 || ev.keyCode == 10) // CR or LF (iPhone+safari)
                that.onEnter();
        });

        // If multichannelquery is undefined, poll the channel automatically.
        // Otherwise have the multichannelquery do the polling in a combined
        // fashion.
        if (typeof multichannelquery == 'undefined') {
            this.poll();
            setInterval(function() { that.poll(); }, 4000);
        } else {
            multichannelquery.addChannel(channel_id, this);
        }
    };

    // Make channel inheritable
    Channel.prototype = new Object();
    Channel.prototype.constructor = Channel;

    Channel.prototype.addLinks = function(body) {
        return body
                .replace(/(^|\s+)(https?:\/\/)(\S+)/, '$1<a href="$2$3" target="_blank">$3</a>')
                .replace(/(^|\s+)(www\.)(\S+)/, '$1<a href="http://$2$3" target="_blank">$3</a>')
        ;
    };

    Channel.prototype.addMessages = function(messages) {
        var dst = this.output_field;
        for (var i = 0, j = messages.length; i < j; ++i) {
            // It's quite possible that we get the same results for an old query
            // In theory it's even possible that we lose messages because
            // an old message has not arrived yet but is now skipped because
            // of this check. We'll deal with that if it becomes a real issue.
            if (messages[i]['id'] <= this.last_message_id)
                continue;
            $('<div class="message' + ('extra_class' in messages[i] ? ' ' + messages[i]['extra_class'] : '') + '">'
            + '<span class="time">' + this.htmlentities(messages[i]['time']) + ' </span>'
            + '<span class="sender">'
                + (messages[i]['sender'] != null ? (this.htmlentities(messages[i]['sender']) + ': ') : '*** ')
                + '</span>'
            + '<span class="body">' + this.addLinks(this.htmlentities(messages[i]['body'])) + '</span>'
            + '</div>').appendTo(dst);
        }
        if (i > 0) {
            this.last_message_id = messages[i - 1]['id'];
        }
    };

    Channel.prototype.htmlentities = function(str) {
        return str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;');
    };

    Channel.prototype.doQuery = function(optionalbody) {
        var that = this;
        var dict = {
            'cache': false,
            'dataType': 'json',
            'error': function(req, textstatus, error) { that.onError(); },
            'success': function(data) { that.onMessages(data); },
            'url': this.userchat_url + '?gt=' + this.last_message_id
        };
        if (typeof optionalbody == 'undefined') {
            dict['type'] = 'GET';
        } else {
            dict['type'] = 'POST';
            dict['data'] = {'body': optionalbody};
        }
        jQuery.ajax(dict);
    };

    Channel.prototype.poll = function() {
        this.doQuery();
    };

    Channel.prototype.onEnter = function() {
        var value = this.input_field.value.replace(/^\s+|\s+$/g, ''); //.trim();
        if (value != '') {
            this.input_field.value = '';
            this.doQuery(value);
        }
    };

    Channel.prototype.onError = function() {
        if (!this.input_field.disabled) {
            this.input_field.disabled = true;
            this.input_field.className += ' connection-error';
            this.output_field.className += ' connection-error';
        }
    };

    Channel.prototype.onMessages = function(messages) {
        // New messages? Undo all we did in onError
        if (this.input_field.disabled) {
            this.input_field.disabled = false;
            this.input_field.className = this.input_field.className
                    .replace(/\bconnection-error\b/, '').replace(/^\s+|\s+$/g, '');
            this.output_field.className = this.output_field.className
                    .replace(/\bconnection-error\b/, '').replace(/^\s+|\s+$/g, '');
        }
        // Check the scrollbar position. Are we at the bottom?
        var may_scroll = (this.output_field.scrollHeight - this.output_field.scrollTop - this.output_field.offsetHeight) <= 5;
        // Add messages to the output_field
        this.addMessages(messages);
        // If we were at the bottom, scroll down for the new messages.
        if (may_scroll)
            this.scrollDown();
    };

    Channel.prototype.scrollDown = function() {
        this.output_field.scrollTop = this.output_field.scrollHeight; // minus offsetHeight, actually
    };


    var MultiChannelQuery = function(userchat_url, on_messages) {
        this.userchat_url = userchat_url; // default: "/im/multiq/"
        this.on_messages = on_messages;
        this.channels = {}

        var that = this;

        // Set a timer for data polling
        setInterval(function() { that.poll(true); }, 4000);
    };

    // Make channel inheritable
    MultiChannelQuery.prototype = new Object();
    MultiChannelQuery.prototype.constructor = MultiChannelQuery;

    MultiChannelQuery.prototype.addChannel = function(channel_id, channel) {
        this.channels[channel_id] = channel;
    };

    MultiChannelQuery.prototype.poll = function(notify_listeners) {
        // Set notify_listeners to false if you don't want the custom on_messages
        // function called. Useful for the first poll of the page.
        var i, channels = [];
        for (i in this.channels) {
            channels.push(i);
            channels.push(this.channels[i].last_message_id);
        }

        if (channels.length == 0)
            return;

        var that = this;
        var dict = {
            'type': 'GET',
            'cache': false,
            'dataType': 'json',
            'error': function(req, textstatus, error) { that.onError(); },
            'success': function(data) { that.onMultipleMessages(data, notify_listeners); },
            'url': this.userchat_url + '?q=' + channels.join('-')
        };
        jQuery.ajax(dict);
    };
    
    MultiChannelQuery.prototype.onError = function() {
        for (var i in this.channels) {
            this.channels[i].onError();
        }
    };

    MultiChannelQuery.prototype.onMultipleMessages = function(channel_messages, notify_listeners) {
        // Call onMessages for every channel, not only those in
        // channel_messages because Channel.onMessages undoes any
        // previous onError behaviour.
        var channel_ids = [];
        for (var i in this.channels) {
            if (i in channel_messages) {
                this.channels[i].onMessages(channel_messages[i]);
                channel_ids.push(i);
            } else {
                this.channels[i].onMessages([]);
            }
        }
        if (channel_ids.length && typeof this.on_messages != 'undefined' && notify_listeners) {
            this.on_messages(channel_ids);
        }
    };


    // Add the classes to the osso.userchat namespace and free the globals.
    window.osso.userchat = {
        'Channel': Channel,
        'MultiChannelQuery': MultiChannelQuery
    };
    Channel = MultiChannelQuery = undefined;
}
