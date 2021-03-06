/*jshint esversion: 6 */

import { Map, List, Collection } from "immutable/dist/immutable";
import Immutable from "immutable/dist/immutable";

const isArrayObject = Array.isArray;

const isPlainObject = function(v) {
    return (v && (v.constructor === Object || v.constructor === undefined));
};

const isImmutable = Immutable.Iterable.isIterable;

const isImmutableMap = Immutable.Map.isMap;

const isImmutableList = Immutable.List.isList;

// A consistent shared value representing "not set" which equals nothing other
// than itself, and nothing that could be provided externally.
const NOT_SET_VALUE = {};

function formatPath(path) {

    const iter = path[Symbol.iterator]();

    let part = iter.next();
    if (part.done) {
        return '';
    }

    const parts = [];
    const value = part.value;
    if (Number.isInteger(value)) {
        parts.push(`[${value}]`);
    } else {
        parts.push(value);
    }

    for (part = iter.next(); !part.done; part = iter.next()) {
        const value = part.value;
        if (Number.isInteger(value)) {
            parts.push(`[${value}]`);
        } else {
            parts.push('.');
            parts.push(value);
        }
    }

    return parts.join('');
}

export {
    isArrayObject,
    isPlainObject,
    isImmutable,
    isImmutableMap,
    isImmutableList,
    formatPath,
    NOT_SET_VALUE
};
