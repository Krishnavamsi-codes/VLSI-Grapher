// Presentation demo: U1 reads missing_signal, but no gate or input drives it.
module demo_floating_input (a, b, y);
  input a, b;
  output y;
  wire n1, missing_signal;

  NAND2_X1M_A9TH U1 (.A(a), .B(missing_signal), .Y(n1));
  INV_X1M_A9TH   U2 (.A(n1), .Y(y));
endmodule
