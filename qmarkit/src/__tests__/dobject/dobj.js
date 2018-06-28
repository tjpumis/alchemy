/*jshint esversion: 6 */

import dobject from "../../dobject";

let jsobj = {
    a: {
        b: {
            c: 100,
        },
        x: {
            y: 200,
        }
    }
};


test("dobject get and set", () => {
    let obj = dobject.fromJS(jsobj);

    expect(obj).toBeInstanceOf(dobject.DObject);
    expect(obj.a).toBeInstanceOf(dobject.DObject);
    expect(obj.a.b).toBeInstanceOf(dobject.DObject);

    expect(obj.a.b.c).toBe(100);

    obj.a.b.c = 101;

    expect(obj.a.b.c).toBe(101);
});

test("dobject snapshot", () => {
    let obj = dobject.fromJS(jsobj);

    expect(obj.a.b.c).toBe(100);

    let r1 = dobject.snapshot(obj);
    let r1_a = dobject.snapshot(obj.a);
    let r1_a_b = dobject.snapshot(obj.a.b);
    let r1_a_x = dobject.snapshot(obj.a.x);

    expect(r1_a_b.isSameAs(r1_a_b)).toBeTruthy();
    expect(r1_a_b.isSameAs(obj.a.b)).toBeTruthy();
    expect(r1_a_b.isSameAs(obj.a)).toBeFalsy();

    obj.a.b.c = 200;

    expect(obj.a.b.c).toBe(200);
    expect(r1_a_b.isSameAs(obj.a.b)).toBeFalsy();
    expect(r1_a.isSameAs(obj.a)).toBeFalsy();
    expect(r1.isSameAs(obj)).toBeFalsy();
    expect(r1_a_x.isSameAs(obj.a.x)).toBeTruthy();
});
