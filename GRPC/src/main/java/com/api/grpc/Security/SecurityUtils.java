package com.api.grpc.Security;

import org.apache.commons.text.StringEscapeUtils;

public class SecurityUtils {

    public static String sanitize(String input) {
        if (input == null) return null;
        return StringEscapeUtils.escapeHtml4(input);
    }
}
