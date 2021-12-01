"""
pytube patch until:

https://github.com/pytube/pytube/issues/1163

gets fixed

"""
import pytube.parser
import re


def throttling_array_split(js_array):
    """Parses the throttling array into a python list of strings.
    Expects input to begin with `[` and close with `]`.
    :param str js_array:
        The javascript array, as a string.
    :rtype: list:
    :returns:
        A list of strings representing splits on `,` in the throttling array.
    """
    results = []
    curr_substring = js_array[1:]

    comma_regex = re.compile(r",")
    func_regex = re.compile(r"function\([^)]+\)")

    while len(curr_substring) > 0:
        if curr_substring.startswith("function"):
            # Handle functions separately. These can contain commas
            match = func_regex.search(curr_substring)
            match_start, match_end = match.span()

            function_text = pytube.parser.find_object_from_startpoint(
                curr_substring, match.span()[1]
            )
            full_function_def = curr_substring[: match_end + len(function_text)]
            results.append(full_function_def)
            curr_substring = curr_substring[len(full_function_def) + 1 :]
        else:
            match = comma_regex.search(curr_substring)

            # Try-catch to capture end of array
            try:
                match_start, match_end = match.span()
            except AttributeError:
                match_start = len(curr_substring) - 1
                match_end = match_start + 1

            curr_el = curr_substring[:match_start]
            results.append(curr_el)
            curr_substring = curr_substring[match_end:]

    return results


pytube.parser.throttling_array_split = throttling_array_split
